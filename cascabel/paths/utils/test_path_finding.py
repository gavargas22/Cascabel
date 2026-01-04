"""
Test script for path finding functionality.
Run this to test the get_optimal_path function.
"""
from path_finding import get_optimal_path, get_optimal_path_feature, load_graph
import json

# Example coordinates (longitude, latitude)
starting_point = (-106.48200897884115, 31.742924505438225)
ending_point = (-106.48665200757424, 31.750015016415418)

print("Testing path finding...")
print(f"Start: {starting_point}")
print(f"End: {ending_point}")
print()

# Test 1: Get optimal path as LineString (loading graph automatically)
print("Test 1: Get LineString with automatic graph loading")
linestring = get_optimal_path(starting_point, ending_point)
print(f"Result type: {linestring['type']}")
print(f"Number of coordinates: {len(linestring['coordinates'])}")
print(f"First coordinate: {linestring['coordinates'][0]}")
print(f"Last coordinate: {linestring['coordinates'][-1]}")
print()

# Test 2: Pre-load graph for multiple queries (more efficient)
print("Test 2: Pre-load graph for reuse")
graph = load_graph("paso_del_norte")
linestring2 = get_optimal_path(starting_point, ending_point, graph=graph)
print(f"Number of coordinates: {len(linestring2['coordinates'])}")
print()

# Test 3: Get as GeoJSON Feature with properties
print("Test 3: Get as GeoJSON Feature")
feature = get_optimal_path_feature(
    starting_point,
    ending_point,
    graph=graph,
    properties={"name": "Test Route", "type": "optimal"}
)
print(f"Feature type: {feature['type']}")
print(f"Geometry type: {feature['geometry']['type']}")
print(f"Properties: {feature['properties']}")
print()

# Export example
print("Example GeoJSON output:")
print(json.dumps(feature, indent=2))
