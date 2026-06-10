"""
Build space syntax graph from DXF:
1. Reconstruct closed room polygons from line segments per floor
2. For each door line, find the two rooms it connects (intersection / proximity)
3. Build a NetworkX graph: nodes = rooms, edges = door connections
4. Compute integration, connectivity, mean_depth, step_depth from entrance
5. Merge into dataset
"""
import ezdxf
import pandas as pd
import numpy as np
import networkx as nx
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union, polygonize, linemerge
from collections import defaultdict

doc = ezdxf.readfile('/mnt/user-data/uploads/taskisla2.dxf')
msp = doc.modelspace()

LAYER_MAP = {
    '01_ROOMS$basement_rooms': 'basement',
    '01_ROOMS$ground_rooms':   'ground',
    '01_ROOMS$floor1_rooms':   'floor1',
    '01_ROOMS$floor2_rooms':   'floor2',
}
DOOR_LAYER = '02_DOORS$doors'

# Collect lines per floor + doors
floor_lines = {fl: [] for fl in LAYER_MAP.values()}
door_lines = []

for e in msp:
    if e.dxftype() != 'LINE':
        continue
    layer = e.dxf.layer
    s = (e.dxf.start.x, e.dxf.start.y)
    t = (e.dxf.end.x, e.dxf.end.y)
    if layer in LAYER_MAP:
        floor_lines[LAYER_MAP[layer]].append(LineString([s, t]))
    elif layer == DOOR_LAYER:
        door_lines.append(LineString([s, t]))

print(f'Door lines: {len(door_lines)}')
for fl, lines in floor_lines.items():
    print(f'{fl}: {len(lines)} line segments')

# Reconstruct polygons per floor using shapely polygonize
floor_polygons = {}
for fl, lines in floor_lines.items():
    merged = linemerge(lines)
    polys = list(polygonize(unary_union(lines)))
    floor_polygons[fl] = polys
    print(f'{fl}: reconstructed {len(polys)} polygons')

# Now match polygons to dataset rooms using centroid proximity
df = pd.read_excel('/mnt/user-data/uploads/dataset_depthmapx.xlsx')

# For each dataset room with known centroid, find nearest polygon centroid
room_to_polygon = {}  # room_id -> shapely polygon
unmatched = []

for _, row in df.iterrows():
    fl = row['floor']
    cx = row['centroid_x']
    cy = row['centroid_y']
    if pd.isna(cx) or pd.isna(cy):
        unmatched.append(row['room_id'])
        continue
    if fl not in floor_polygons:
        continue
    target = Point(cx, cy)
    best = None
    best_d = float('inf')
    for poly in floor_polygons[fl]:
        d = poly.centroid.distance(target)
        # Prefer polygons that CONTAIN the target point
        if poly.contains(target):
            best = poly
            best_d = 0
            break
        if d < best_d:
            best = poly
            best_d = d
    if best is not None:
        room_to_polygon[row['room_id']] = best
    else:
        unmatched.append(row['room_id'])

print(f'\nMatched {len(room_to_polygon)} rooms to polygons')
print(f'Unmatched: {len(unmatched)} rooms')
if unmatched[:10]:
    print(f'  Examples: {unmatched[:10]}')

# Save intermediate so we can debug
import pickle
with open('/home/claude/ns/state.pkl', 'wb') as f:
    pickle.dump({
        'door_lines': door_lines,
        'floor_polygons': floor_polygons,
        'room_to_polygon': room_to_polygon,
        'unmatched': unmatched,
        'df': df
    }, f)
print('\nSaved state.')
