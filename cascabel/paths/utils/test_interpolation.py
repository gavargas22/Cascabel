"""
Test script to compare path interpolation methods.
Demonstrates the difference between simple node-to-node paths and
detailed paths that follow actual road geometry.
"""

import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from cascabel.paths.utils.path_finding import get_optimal_path, load_graph
import json

# Load graph
print("Loading road network graph...")
graph = load_graph('paso_del_norte')
print(f"Loaded: {len(graph.nodes)} nodes, {len(graph.edges)} edges\n")

# Define route
start = (-106.482, 31.743)
end = (-106.487, 31.750)
print(f"Route: {start} -> {end}\n")

# Get paths with both methods
print("=" * 60)
print("Comparing interpolation methods:")
print("=" * 60)

# Method 1: Simple (node coordinates only)
path_simple = get_optimal_path(start, end, graph=graph, interpolate=False)
print(f"\n1. Simple (interpolate=False):")
print(f"   Vertices: {len(path_simple['coordinates'])}")
print(f"   Description: Uses only graph node coordinates")
print(f"   Result: Straight lines between intersections")

# Method 2: Detailed (with edge geometries)
path_detailed = get_optimal_path(start, end, graph=graph, interpolate=True)
print(f"\n2. Detailed (interpolate=True):")
print(f"   Vertices: {len(path_detailed['coordinates'])}")
print(f"   Description: Uses actual road geometry from OSM")
print(f"   Result: Follows real road curves and details")

# Calculate improvement
improvement = len(path_detailed['coordinates']) / len(path_simple['coordinates'])
additional_vertices = len(path_detailed['coordinates']) - len(path_simple['coordinates'])

print(f"\n{'=' * 60}")
print(f"Improvement Summary:")
print(f"{'=' * 60}")
print(f"  Additional vertices: +{additional_vertices}")
print(f"  Detail increase: {improvement:.1f}x more points")
print(f"  Better curve representation: YES")

# Show coordinate samples
print(f"\n{'=' * 60}")
print(f"Coordinate Samples:")
print(f"{'=' * 60}")

print(f"\nSimple path (first 5 points):")
for i, coord in enumerate(path_simple['coordinates'][:5], 1):
    print(f"  {i}. Lon: {coord[0]:.7f}, Lat: {coord[1]:.7f}")

print(f"\nDetailed path (first 10 points):")
for i, coord in enumerate(path_detailed['coordinates'][:10], 1):
    print(f"  {i}. Lon: {coord[0]:.7f}, Lat: {coord[1]:.7f}")

# Export for visualization
print(f"\n{'=' * 60}")
print(f"Exporting GeoJSON for visualization:")
print(f"{'=' * 60}")

geojson_comparison = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Simple Path",
                "method": "interpolate=False",
                "vertices": len(path_simple['coordinates']),
                "color": "#FF0000"
            },
            "geometry": path_simple
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Detailed Path",
                "method": "interpolate=True",
                "vertices": len(path_detailed['coordinates']),
                "color": "#00FF00"
            },
            "geometry": path_detailed
        }
    ]
}

output_file = "path_comparison.geojson"
with open(output_file, 'w') as f:
    json.dump(geojson_comparison, f, indent=2)

print(f"✓ Saved to: {output_file}")
print(f"  - Red line (simple): {len(path_simple['coordinates'])} vertices")
print(f"  - Green line (detailed): {len(path_detailed['coordinates'])} vertices")
print(f"\nVisualize this file in:")
print(f"  - QGIS")
print(f"  - geojson.io")
print(f"  - Mapbox Studio")
print(f"  - Any GIS software")

print(f"\n{'=' * 60}")
print(f"Recommendation:")
print(f"{'=' * 60}")
print(f"Use interpolate=True (default) for:")
print(f"  ✓ Realistic vehicle movement simulation")
print(f"  ✓ Accurate distance calculations")
print(f"  ✓ Proper curve following")
print(f"  ✓ Better visualization")
print(f"\nUse interpolate=False only if:")
print(f"  - You need minimal data")
print(f"  - Straight lines between nodes are acceptable")
