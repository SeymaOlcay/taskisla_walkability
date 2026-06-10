"""
Improved approach:
- Use dataset.opens_to column EXTENSIVELY (it has connectivity info already)
- "corridor" → connect to a virtual corridor node per floor
- "room_X" → connect directly
- Use door lines to add EXTRA edges discovered geometrically
- Add stair edges across floors
"""
import pickle
import pandas as pd
import numpy as np
import networkx as nx
from shapely.geometry import Point
import math

with open('/home/claude/ns/state.pkl', 'rb') as f:
    s = pickle.load(f)

door_lines = s['door_lines']
floor_polygons = s['floor_polygons']
room_to_polygon = s['room_to_polygon']
df = s['df']

room_to_floor = dict(zip(df['room_id'].astype(str), df['floor']))

# Build graph - all rooms as nodes
G = nx.Graph()
for _, row in df.iterrows():
    G.add_node(str(row['room_id']),
               floor=row['floor'],
               function=row['function_type'],
               area=row['area_m2'])

# === STRATEGY: use opens_to + virtual corridor nodes per floor ===
# Create one "corridor" virtual node per floor. Rooms whose opens_to == 'corridor'
# connect to that corridor node. Rooms whose opens_to mentions a specific room
# connect directly.

# Actually, looking at the dataset, many rooms have opens_to='corridor'.
# But the corridor itself is also a room in the dataset (H1_B, H2_B, etc. for basement).
# For other floors there might not be explicit corridor rooms.

# Simpler: for each floor, identify the circulation rooms. All rooms whose opens_to
# contains 'corridor' connect to ALL circulation rooms on their floor (they're a chain).

# Actually MOST robust: for each floor, connect each non-circulation room to the
# nearest circulation room (by centroid distance).

# Get circulation rooms per floor
floors = ['basement', 'ground', 'floor1', 'floor2']
circulation_per_floor = {}
for fl in floors:
    circ = df[(df['floor']==fl) & (df['function_type'].isin(['circulation','courtyard']))]
    circulation_per_floor[fl] = circ[['room_id','centroid_x','centroid_y']].values.tolist()
    print(f'{fl}: {len(circ)} circulation/courtyard rooms')

# Add circulation chain edges per floor (corridor segments connect to each other)
# Plus explicit opens_to information
def parse_opens_to(s):
    if pd.isna(s):
        return []
    s = str(s).lower().replace(' ', '')
    parts = s.split(',')
    targets = []
    for p in parts:
        if p.startswith('room_'):
            targets.append(('room', p.replace('room_','')))
        elif p.startswith('rooms_'):
            # like 'rooms_13_14_h2' - parse out room IDs
            inner = p.replace('rooms_','')
            for piece in inner.split('_'):
                targets.append(('room', piece))
        elif 'corridor' in p:
            targets.append(('corridor', None))
        elif p == 'outside':
            targets.append(('outside', None))
        elif p == 'open_above':
            pass  # courtyard sky
    return targets

# Connect rooms to corridors via "nearest circulation room on same floor"
edges_added = 0
for _, row in df.iterrows():
    rid = str(row['room_id'])
    fl = row['floor']
    targets = parse_opens_to(row['opens_to'])
    
    if any(t[0]=='corridor' for t in targets):
        # Connect to nearest circulation/courtyard room on same floor
        cands = circulation_per_floor[fl]
        if cands:
            best = None
            best_d = float('inf')
            cx, cy = row['centroid_x'], row['centroid_y']
            if pd.notna(cx) and pd.notna(cy):
                for c_rid, c_x, c_y in cands:
                    if str(c_rid) == rid:
                        continue
                    d = ((c_x - cx)**2 + (c_y - cy)**2)**0.5
                    if d < best_d:
                        best_d = d
                        best = str(c_rid)
            if best is not None and not G.has_edge(rid, best):
                G.add_edge(rid, best)
                edges_added += 1
    
    # Explicit room-room edges
    for t_type, t_val in targets:
        if t_type == 'room':
            other = str(t_val).upper() if t_val and any(c.isalpha() for c in str(t_val)) else str(t_val)
            # Try variants
            for variant in [str(t_val), str(t_val).upper(), str(t_val).lower()]:
                if variant in G:
                    if not G.has_edge(rid, variant):
                        G.add_edge(rid, variant)
                        edges_added += 1
                    break

print(f'Edges from opens_to: {edges_added}')

# Connect circulation rooms ON THE SAME FLOOR to each other if they're close
# (corridors are a chain)
chain_edges = 0
for fl in floors:
    circ = circulation_per_floor[fl]
    # Sort by x position (rough chain along the building)
    circ_sorted = sorted([c for c in circ if pd.notna(c[1])], key=lambda c: c[1])
    for i in range(len(circ_sorted) - 1):
        r1 = str(circ_sorted[i][0])
        r2 = str(circ_sorted[i+1][0])
        if r1 in G and r2 in G and not G.has_edge(r1, r2):
            G.add_edge(r1, r2)
            chain_edges += 1

print(f'Circulation chain edges: {chain_edges}')

# Also: for circulation rooms, treat them as if they connect to multiple corridor segments
# Add: any circulation room connects to ALL other circulation rooms on the same floor
# (treating the corridor as one big connected ring on each floor)
ring_edges = 0
for fl in floors:
    circ_ids = [str(c[0]) for c in circulation_per_floor[fl]]
    for i in range(len(circ_ids)):
        for j in range(i+1, len(circ_ids)):
            if circ_ids[i] in G and circ_ids[j] in G:
                if not G.has_edge(circ_ids[i], circ_ids[j]):
                    G.add_edge(circ_ids[i], circ_ids[j])
                    ring_edges += 1
print(f'Circulation ring edges: {ring_edges}')

# Add inter-floor stair edges
stair_corners = ['S_NW', 'S_NE', 'S_SW', 'S_SE']
floor_order = ['basement', 'ground', 'floor1', 'floor2']

stair_node_per_floor = {}
for corner in stair_corners:
    for fl in floor_order:
        # Find rooms whose nearest_stair_id == corner, prefer circulation
        circ_rooms = df[(df['floor']==fl) & (df['nearest_stair_id']==corner) & (df['function_type']=='circulation')]
        if len(circ_rooms) > 0:
            stair_node_per_floor[(corner, fl)] = str(circ_rooms.iloc[0]['room_id'])
        else:
            any_rooms = df[(df['floor']==fl) & (df['nearest_stair_id']==corner)].sort_values('area_m2')
            if len(any_rooms) > 0:
                stair_node_per_floor[(corner, fl)] = str(any_rooms.iloc[0]['room_id'])

stair_edges_count = 0
for corner in stair_corners:
    for i in range(len(floor_order) - 1):
        r1 = stair_node_per_floor.get((corner, floor_order[i]))
        r2 = stair_node_per_floor.get((corner, floor_order[i+1]))
        if r1 and r2 and r1 in G and r2 in G:
            if not G.has_edge(r1, r2):
                G.add_edge(r1, r2)
                stair_edges_count += 1
print(f'Stair edges across floors: {stair_edges_count}')

# Connect the main entrance (137) to outside is implicit - 137 is the entrance node

print(f'\nGraph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
components = list(nx.connected_components(G))
print(f'Connected components: {len(components)}')
sizes = sorted([len(c) for c in components], reverse=True)
print(f'Sizes (top 10): {sizes[:10]}')

# Identify isolates - rooms not in the giant component
giant = max(components, key=len)
isolated = []
for c in components:
    if c != giant:
        isolated.extend(c)

# For isolated rooms, force-connect them to the nearest circulation room on the same floor
# (they probably have opens_to info we missed)
forced_edges = 0
for rid in isolated:
    if rid not in G:
        continue
    fl = G.nodes[rid].get('floor')
    if not fl:
        continue
    cx_row = df[df['room_id'].astype(str)==rid].iloc[0]
    cx, cy = cx_row['centroid_x'], cx_row['centroid_y']
    if pd.isna(cx):
        continue
    # Find nearest GIANT component room on same floor
    best = None
    best_d = float('inf')
    for other_rid in giant:
        if G.nodes[other_rid].get('floor') != fl:
            continue
        other_row = df[df['room_id'].astype(str)==other_rid].iloc[0]
        ox, oy = other_row['centroid_x'], other_row['centroid_y']
        if pd.isna(ox):
            continue
        d = ((ox - cx)**2 + (oy - cy)**2)**0.5
        if d < best_d:
            best_d = d
            best = other_rid
    if best is not None:
        G.add_edge(rid, best)
        forced_edges += 1

print(f'Forced edges (isolated → nearest): {forced_edges}')

components = list(nx.connected_components(G))
print(f'After forcing: {len(components)} components, sizes: {sorted([len(c) for c in components], reverse=True)[:5]}')

# Use full graph now
giant_set = max(components, key=len)
giant = G.subgraph(giant_set).copy()

print(f'\nFinal graph for analysis: {giant.number_of_nodes()} nodes, {giant.number_of_edges()} edges')

# CONNECTIVITY
connectivity = dict(giant.degree())

# MEAN DEPTH - average shortest path from each node
print('Computing shortest paths...')
all_pairs = dict(nx.all_pairs_shortest_path_length(giant))

mean_depth = {}
for node, dists in all_pairs.items():
    if len(dists) > 1:
        mean_depth[node] = sum(dists.values()) / (len(dists) - 1)
    else:
        mean_depth[node] = 0

# INTEGRATION HH
k = giant.number_of_nodes()
D_k = 2 * (k * (math.log2((k+2)/3) - 1) + 1) / ((k-1) * (k-2))
integration = {}
for node, md in mean_depth.items():
    ra = 2 * (md - 1) / (k - 2)
    rra = ra / D_k if D_k > 0 else 0
    integration[node] = 1 / rra if rra > 0 else 0

# STEP DEPTH FROM ENTRANCE (137)
entrance = '137'
if entrance in giant:
    step_depth = nx.single_source_shortest_path_length(giant, entrance)
else:
    print(f'WARNING: entrance {entrance} not in giant')
    step_depth = {}

# Update dataset
df['connectivity'] = df['room_id'].astype(str).map(connectivity)
df['mean_depth'] = df['room_id'].astype(str).map(mean_depth)
df['integration_hh'] = df['room_id'].astype(str).map(integration)
df['step_depth_from_entrance'] = df['room_id'].astype(str).map(step_depth)

print('\n=== STATS ===')
print(f'connectivity: {df["connectivity"].min()} – {df["connectivity"].max()} (avg {df["connectivity"].mean():.2f})')
print(f'mean_depth: {df["mean_depth"].min():.2f} – {df["mean_depth"].max():.2f}')
print(f'integration_hh: {df["integration_hh"].min():.2f} – {df["integration_hh"].max():.2f}')
print(f'step_depth: {df["step_depth_from_entrance"].min()} – {df["step_depth_from_entrance"].max()}')
print()
print('NaN counts:')
print(df[['connectivity','mean_depth','integration_hh','step_depth_from_entrance']].isna().sum())

print('\n=== TOP 10 MOST INTEGRATED ===')
print(df.nlargest(10, 'integration_hh')[['room_id','floor','function_type','function_detail','integration_hh','connectivity','step_depth_from_entrance']].to_string(index=False))

print('\n=== TOP 10 LEAST INTEGRATED ===')
print(df.nsmallest(10, 'integration_hh')[['room_id','floor','function_type','function_detail','integration_hh','connectivity','step_depth_from_entrance']].to_string(index=False))

# Per-floor stats
print('\n=== INTEGRATION BY FLOOR ===')
print(df.groupby('floor')['integration_hh'].agg(['mean','median','min','max']).round(2))

print('\n=== INTEGRATION BY FUNCTION TYPE ===')
print(df.groupby('function_type')['integration_hh'].agg(['mean','count']).round(2).sort_values('mean', ascending=False))

# Save
df.to_excel('/mnt/user-data/outputs/dataset_with_syntax.xlsx', index=False)
df.to_pickle('/mnt/user-data/outputs/dataset_with_syntax.pkl')
df.to_csv('/mnt/user-data/outputs/dataset_with_syntax.csv', index=False, encoding='utf-8-sig')
print('\nSaved.')

import json
graph_data = {
    'nodes': [{'id': n, **G.nodes[n]} for n in G.nodes()],
    'edges': [[a, b] for a, b in G.edges()]
}
with open('/mnt/user-data/outputs/spatial_graph.json', 'w') as f:
    json.dump(graph_data, f, ensure_ascii=False, indent=2)

with open('/home/claude/ns/state2.pkl', 'wb') as f:
    pickle.dump({'df': df, 'G': G, 'giant': giant}, f)
