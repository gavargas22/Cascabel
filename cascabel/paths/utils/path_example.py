"""
Cascabel Path Finding Example
A simple interactive example using Marimo to demonstrate path finding utilities.
Run with: marimo edit cascabel/paths/utils/path_example.py
"""

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    mo.md(
        """
        # Cascabel Path Finding Demo

        This notebook demonstrates how to use the Cascabel path finding utilities to:
        - Load OpenStreetMap road network graphs
        - Find optimal paths between two points
        - Visualize routes on a map
        """
    )

    return (mo,)


@app.cell
def _():
    import os
    import json
    import sys

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    sys.path.insert(0, root_dir)
    return (json,)


@app.cell
def _():
    # Import path utilities
    from cascabel.paths.utils.path_finding import (
        get_optimal_path,
        get_optimal_path_feature,
        load_graph
    )
    from cascabel.paths.utils.graph_retrieval import load_bounding_boxes
    return (
        get_optimal_path,
        get_optimal_path_feature,
        load_bounding_boxes,
        load_graph,
    )


@app.cell
def _(mo):
    mo.md("""
    ## Step 1: Load the Road Network

    First, we'll load the cached road network graph for the Paso del Norte area.
    """)
    return


@app.cell
def _(load_bounding_boxes, load_graph):
    # Load available areas
    bounding_boxes = load_bounding_boxes()
    print(f"Available areas: {list(bounding_boxes.keys())}")

    # Load the graph for Paso del Norte
    graph = load_graph("paso_del_norte")
    print(f"\nGraph loaded: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    return (graph,)


@app.cell
def _(mo):
    mo.md("""
    ## Step 2: Define Start and End Points

    Select or input coordinates for your route. Coordinates are in (longitude, latitude) format.

    **Example locations:**
    - Highway Entrance: (-106.482, 31.743)
    - Border Crossing: (-106.487, 31.750)
    """)
    return


@app.cell
def _(mo):
    # Input widgets for coordinates
    start_lon = mo.ui.number(
        value=-106.482,
        label="Start Longitude",
        step=0.001
    )
    start_lat = mo.ui.number(
        value=31.743,
        label="Start Latitude",
        step=0.001
    )

    end_lon = mo.ui.number(
        value=-106.487,
        label="End Longitude",
        step=0.001
    )
    end_lat = mo.ui.number(
        value=31.750,
        label="End Latitude",
        step=0.001
    )

    mo.hstack([
        mo.vstack([start_lon, start_lat]),
        mo.vstack([end_lon, end_lat])
    ])
    return end_lat, end_lon, start_lat, start_lon


@app.cell
def _(end_lat, end_lon, start_lat, start_lon):
    # Create coordinate tuples
    starting_point = (start_lon.value, start_lat.value)
    ending_point = (end_lon.value, end_lat.value)

    print(f"Route from {starting_point} to {ending_point}")
    return ending_point, starting_point


@app.cell
def _(mo):
    mo.md("""
    ## Step 3: Calculate Optimal Path

    Now we'll find the shortest path between the two points using the road network.
    """)
    return


@app.cell
def _(ending_point, get_optimal_path, graph, starting_point):
    # Calculate the optimal path
    path = get_optimal_path(
        starting_point,
        ending_point,
        graph=graph,
        weight="length",  # Can also use "travel_time"
        interpolate=True
    )

    print(f"Path type: {path['type']}")
    print(f"Number of waypoints: {len(path['coordinates'])}")
    print(f"\nFirst 3 coordinates:")
    for i, coord in enumerate(path['coordinates'][:3]):
        print(f"  {i+1}. [{coord[0]:.6f}, {coord[1]:.6f}]")
    return (path,)


@app.cell
def _(mo):
    mo.md("""
    ## Step 4: View Path as GeoJSON

    The path is returned as a GeoJSON LineString, which can be used for visualization.
    """)
    return


@app.cell
def _(json, path):
    # Display the path as formatted JSON
    print(json.dumps(path, indent=2))
    return


@app.cell
def _(mo):
    mo.md("""
    ## Step 5: Create a GeoJSON Feature

    Add metadata to the path by creating a full GeoJSON Feature.
    """)
    return


@app.cell
def _(ending_point, get_optimal_path_feature, graph, starting_point):
    # Create a feature with properties
    feature = get_optimal_path_feature(
        starting_point,
        ending_point,
        graph=graph,
        properties={
            "name": "Example Route",
            "type": "optimal",
            "description": "Shortest path from highway entrance to border crossing"
        }
    )

    print(f"Feature type: {feature['type']}")
    print(f"Properties: {feature['properties']}")
    return (feature,)


@app.cell
def _(mo):
    mo.md("""
    ## Step 6: Simple Map Visualization

    Display the route coordinates in a simple format.
    """)
    return


@app.cell
def _(feature):
    print(feature)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Advanced: Multiple Routes

    You can calculate multiple routes efficiently by reusing the loaded graph.
    """)
    return


@app.cell
def _(get_optimal_path, graph):
    # Example: Calculate multiple routes
    routes = [
        {
            "name": "Route 1",
            "start": (-106.482, 31.743),
            "end": (-106.487, 31.750)
        },
        {
            "name": "Route 2",
            "start": (-106.485, 31.745),
            "end": (-106.490, 31.752)
        }
    ]

    print("Calculating multiple routes:")
    for route in routes:
        try:
            path_result = get_optimal_path(
                route["start"],
                route["end"],
                graph=graph
            )
            print(f"  {route['name']}: {len(path_result['coordinates'])} waypoints")
        except Exception as e:
            print(f"  {route['name']}: Error - {e}")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Summary

    This notebook demonstrated:

    1. ✅ Loading cached road network graphs
    2. ✅ Defining start and end coordinates
    3. ✅ Calculating optimal paths
    4. ✅ Working with GeoJSON output
    5. ✅ Calculating multiple routes efficiently

    ### Next Steps

    - Try different start/end coordinates
    - Experiment with `weight="travel_time"` vs `weight="length"`
    - Export the GeoJSON to visualize in QGIS or other mapping tools
    - Use the paths in the Cascabel simulation

    ### API Reference

    ```python
    # Load a graph
    graph = load_graph("paso_del_norte")

    # Get optimal path as LineString
    path = get_optimal_path(start, end, graph=graph)

    # Get optimal path as Feature with metadata
    feature = get_optimal_path_feature(
        start, end,
        graph=graph,
        properties={"name": "My Route"}
    )
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
