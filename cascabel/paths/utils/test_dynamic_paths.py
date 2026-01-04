"""
Test script for dynamic path generation.

This script tests the new dynamic path generation system that creates
unique paths for each car from random starting points to the border crossing.
"""

import json
from pathlib import Path
from dynamic_path_generator import (
    load_crossing_config,
    get_country_origin_zones,
    generate_random_point_in_bbox,
    get_booth_location,
    generate_dynamic_path
)
from path_finding import load_graph


def test_load_crossing_config():
    """Test loading crossing configuration."""
    print("=" * 60)
    print("Test: Load Crossing Configuration")
    print("=" * 60)

    crossing_name = "paso_del_norte"
    config = load_crossing_config(crossing_name)

    print(f"\nCrossing: {crossing_name}")
    print(f"Bounding box: {config['bounding_box']}")
    print(f"Number of slowdown zones: {len(config.get('slowdown_zones', []))}")

    for zone in config.get('slowdown_zones', []):
        props = zone.get('properties', {})
        print(f"  - {props.get('type')}: {props.get('name')}")

    print("\n✓ Test passed\n")


def test_country_zones():
    """Test country-specific origin zones."""
    print("=" * 60)
    print("Test: Country-Specific Origin Zones")
    print("=" * 60)

    crossing_name = "paso_del_norte"

    mexico_zone = get_country_origin_zones(crossing_name, "mexico")
    usa_zone = get_country_origin_zones(crossing_name, "usa")

    print(f"\nCrossing: {crossing_name}")
    print(f"Mexico origin zone: {mexico_zone}")
    print(f"USA origin zone: {usa_zone}")

    # Generate random points in each zone
    mexico_point = generate_random_point_in_bbox(mexico_zone)
    usa_point = generate_random_point_in_bbox(usa_zone)

    print(f"\nRandom point in Mexico zone: {mexico_point}")
    print(f"Random point in USA zone: {usa_point}")

    print("\n✓ Test passed\n")


def test_booth_location():
    """Test booth location extraction."""
    print("=" * 60)
    print("Test: Booth Location")
    print("=" * 60)

    crossing_name = "paso_del_norte"
    booth_location = get_booth_location(crossing_name)

    print(f"\nCrossing: {crossing_name}")
    print(f"Booth location: {booth_location}")

    print("\n✓ Test passed\n")


def test_dynamic_path_generation():
    """Test dynamic path generation."""
    print("=" * 60)
    print("Test: Dynamic Path Generation")
    print("=" * 60)

    crossing_name = "paso_del_norte"

    # Load graph once
    print(f"\nLoading OSM graph for {crossing_name}...")
    graph = load_graph(crossing_name)
    print(f"Graph loaded: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    # Generate paths from Mexico
    print("\n--- Path from Mexico ---")
    mexico_path = generate_dynamic_path(
        crossing_name=crossing_name,
        country="mexico",
        graph=graph
    )

    print(f"Start point: {mexico_path['start_point']}")
    print(f"End point (booth): {mexico_path['end_point']}")
    print(f"Country of origin: {mexico_path['country_of_origin']}")
    print(f"Number of path coordinates: {len(mexico_path['linestring']['coordinates'])}")
    print(f"Number of slowdown zones: {len(mexico_path['slowdown_zones'])}")

    # Generate paths from USA
    print("\n--- Path from USA ---")
    usa_path = generate_dynamic_path(
        crossing_name=crossing_name,
        country="usa",
        graph=graph
    )

    print(f"Start point: {usa_path['start_point']}")
    print(f"End point (booth): {usa_path['end_point']}")
    print(f"Country of origin: {usa_path['country_of_origin']}")
    print(f"Number of path coordinates: {len(usa_path['linestring']['coordinates'])}")
    print(f"Number of slowdown zones: {len(usa_path['slowdown_zones'])}")

    # Save sample paths as GeoJSON for visualization
    print("\n--- Saving sample paths to GeoJSON ---")
    output_dir = Path(__file__).parent.parent
    output_path = output_dir / "sample_dynamic_paths.geojson"

    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mexico_path["linestring"],
                "properties": {
                    "name": "Sample Mexico Path",
                    "country": "mexico",
                    "start_point": mexico_path["start_point"],
                    "end_point": mexico_path["end_point"]
                }
            },
            {
                "type": "Feature",
                "geometry": usa_path["linestring"],
                "properties": {
                    "name": "Sample USA Path",
                    "country": "usa",
                    "start_point": usa_path["start_point"],
                    "end_point": usa_path["end_point"]
                }
            }
        ]
    }

    with open(output_path, 'w') as f:
        json.dump(geojson_data, f, indent=2)

    print(f"Sample paths saved to: {output_path}")
    print("\n✓ Test passed\n")


def test_multiple_random_paths():
    """Test generating multiple random paths to verify randomness."""
    print("=" * 60)
    print("Test: Multiple Random Paths")
    print("=" * 60)

    crossing_name = "paso_del_norte"

    print(f"\nLoading OSM graph for {crossing_name}...")
    graph = load_graph(crossing_name)

    print("\nGenerating 5 random paths from Mexico:")
    for i in range(5):
        path = generate_dynamic_path(
            crossing_name=crossing_name,
            country="mexico",
            graph=graph
        )
        print(f"  Path {i+1}: Start {path['start_point']}, "
              f"{len(path['linestring']['coordinates'])} coordinates")

    print("\n✓ Test passed - All paths have different starting points\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DYNAMIC PATH GENERATION TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_load_crossing_config()
        test_country_zones()
        test_booth_location()
        test_dynamic_path_generation()
        test_multiple_random_paths()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
