"""
Fill in perimeter_m and nearest_stair_distance_m.
- perimeter_m: from reconstructed room polygons in DXF
- nearest_stair_distance_m: from centroid to nearest stair corner
"""
import pickle
import pandas as pd
import numpy as np

with open('/home/claude/ns/state.pkl', 'rb') as f:
    s = pickle.load(f)

room_to_polygon = s['room_to_polygon']

# Load the syntax-enriched dataset
df = pd.read_excel('/mnt/user-data/outputs/dataset_with_syntax.xlsx')

# === 1. PERIMETER ===
perimeters = {}
for room_id, poly in room_to_polygon.items():
    perimeters[str(room_id)] = round(poly.length, 2)

df['perimeter_m'] = df['room_id'].astype(str).map(perimeters)
print(f'Perimeter filled: {df["perimeter_m"].notna().sum()} / {len(df)}')
print(f'  range: {df["perimeter_m"].min():.1f} - {df["perimeter_m"].max():.1f} m')

# === 2. NEAREST STAIR DISTANCE ===
# Stair corners: identify centroid of each stair corner per floor
# A stair corner is the centroid of the rooms whose nearest_stair_id matches that corner
# But that's circular. Better: compute the actual corner positions.
# In Taşkışla, the 4 stair corners are at the building corners.

# For each floor, find the bounding box of all rooms and use the 4 corners
floor_corners = {}
for fl in df['floor'].unique():
    sub = df[df['floor'] == fl]
    if len(sub) == 0:
        continue
    xs = sub['centroid_x'].dropna().values
    ys = sub['centroid_y'].dropna().values
    if len(xs) == 0:
        continue
    xmin, xmax = xs.min(), xs.max()
    ymin, ymax = ys.min(), ys.max()
    floor_corners[fl] = {
        'S_SW': (xmin, ymin),
        'S_SE': (xmax, ymin),
        'S_NW': (xmin, ymax),
        'S_NE': (xmax, ymax),
    }

# For each room, compute distance to its assigned nearest_stair_id corner
distances = []
for _, row in df.iterrows():
    fl = row['floor']
    stair_id = row['nearest_stair_id']
    cx, cy = row['centroid_x'], row['centroid_y']
    if pd.isna(cx) or pd.isna(cy) or fl not in floor_corners:
        distances.append(np.nan)
        continue
    if stair_id in floor_corners[fl]:
        sx, sy = floor_corners[fl][stair_id]
        d = ((sx - cx)**2 + (sy - cy)**2)**0.5
        distances.append(round(d, 2))
    else:
        # If stair_id is unknown, find the actually nearest corner
        best = min(floor_corners[fl].values(),
                   key=lambda c: (c[0]-cx)**2 + (c[1]-cy)**2)
        d = ((best[0]-cx)**2 + (best[1]-cy)**2)**0.5
        distances.append(round(d, 2))

df['nearest_stair_distance_m'] = distances
print(f'Stair distance filled: {df["nearest_stair_distance_m"].notna().sum()} / {len(df)}')
print(f'  range: {df["nearest_stair_distance_m"].min():.1f} - {df["nearest_stair_distance_m"].max():.1f} m')

# Drop the unused 'notes' column if it's all NaN
if 'notes' in df.columns and df['notes'].isna().all():
    df = df.drop(columns=['notes'])
    print("Dropped empty 'notes' column.")

# Final NaN check
print('\nFinal NaN counts:')
print(df.isna().sum()[df.isna().sum() > 0])
if df.isna().sum().sum() == 0:
    print('  No NaN values anywhere! Dataset is complete.')

# Save final
df.to_excel('/mnt/user-data/outputs/dataset_final.xlsx', index=False)
df.to_pickle('/mnt/user-data/outputs/dataset_final.pkl')
df.to_csv('/mnt/user-data/outputs/dataset_final.csv', index=False, encoding='utf-8-sig')

print(f'\nFinal dataset: {df.shape[0]} rows × {df.shape[1]} columns')
print(f'Columns: {df.columns.tolist()}')
