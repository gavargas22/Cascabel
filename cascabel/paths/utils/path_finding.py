import osmnx as ox
import networkx as nx
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from shapely.geometry import LineString, Point
from .graph_retrieval import retrieve_and_cache_graph, load_bounding_boxes

bounding_boxes_path = Path(__file__).parent.parent / "bounding_boxes.json"

def load_graph(area_name: str = "paso_del_norte") -> nx.MultiDiGraph:
    """
    Load a cached graph for the specified area.

    Args:
        area_name: Name of the area (should match a key in bounding_boxes.json)

    Returns:
        NetworkX MultiDiGraph representing the road network
    """
    bounding_boxes = load_bounding_boxes()
    if area_name not in bounding_boxes:
        raise ValueError(f"Area '{area_name}' not found in bounding_boxes.json")

    return retrieve_and_cache_graph(area_name, bounding_boxes[area_name])

def _extract_edge_geometry(graph: nx.MultiDiGraph, u: int, v: int) -> List[List[float]]:
    """
    Extract the geometry of an edge, including intermediate points if available.

    Args:
        graph: The road network graph
        u: Start node ID
        v: End node ID

    Returns:
        List of [lon, lat] coordinate pairs representing the edge geometry
    """
    coords = []

    # Get all edges between u and v (there might be multiple)
    edge_data = graph.get_edge_data(u, v)

    if edge_data:
        # Use the first edge (key 0) if multiple exist
        edge = edge_data.get(0, edge_data[list(edge_data.keys())[0]])

        # Check if the edge has geometry attribute (detailed LineString)
        if 'geometry' in edge:
            # Extract all coordinates from the LineString geometry
            geom = edge['geometry']
            coords = [[point[0], point[1]] for point in geom.coords]
        else:
            # No geometry, just use start and end nodes
            start_x, start_y = graph.nodes[u]['x'], graph.nodes[u]['y']
            end_x, end_y = graph.nodes[v]['x'], graph.nodes[v]['y']
            coords = [[start_x, start_y], [end_x, end_y]]

    return coords


def get_optimal_path(
    starting_point: Tuple[float, float],
    ending_point: Tuple[float, float],
    graph: Optional[nx.MultiDiGraph] = None,
    area_name: str = "paso_del_norte",
    weight: str = "length",
    interpolate: bool = True
) -> Dict[str, Any]:
    """
    Calculate the optimal path between two points and return as a GeoJSON LineString.

    This function uses the actual edge geometries from OpenStreetMap, which includes
    all the curves and details of the real roads, not just straight lines between nodes.

    Args:
        starting_point: Tuple of (longitude, latitude) for the starting location
        ending_point: Tuple of (longitude, latitude) for the ending location
        graph: Optional pre-loaded graph. If None, will load from area_name
        area_name: Name of the area to load graph from (if graph not provided)
        weight: Edge attribute to minimize ('length' or 'travel_time')
        interpolate: If True, use edge geometries for detailed curves (default: True)

    Returns:
        GeoJSON LineString dictionary with the optimal path coordinates
        Format: {"type": "LineString", "coordinates": [[lon, lat], ...]}
    """
    # Load graph if not provided
    if graph is None:
        graph = load_graph(area_name)

    # Snap starting and ending points to nearest nodes
    # ox.distance.nearest_nodes expects (G, X, Y) where X=longitude, Y=latitude
    origin_node = ox.distance.nearest_nodes(graph, starting_point[0], starting_point[1])
    target_node = ox.distance.nearest_nodes(graph, ending_point[0], ending_point[1])

    # Compute shortest path
    path_nodes = nx.shortest_path(graph, origin_node, target_node, weight=weight)

    if not interpolate:
        # Simple mode: just use node coordinates
        route_coords = [[graph.nodes[n]['x'], graph.nodes[n]['y']] for n in path_nodes]
    else:
        # Detailed mode: extract edge geometries for accurate road following
        route_coords = []

        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge_coords = _extract_edge_geometry(graph, u, v)

            if i == 0:
                # First edge: include all points
                route_coords.extend(edge_coords)
            else:
                # Subsequent edges: skip first point to avoid duplicates
                route_coords.extend(edge_coords[1:])

    # Return as GeoJSON LineString
    return {"type": "LineString", "coordinates": route_coords}

def get_optimal_path_feature(
    starting_point: Tuple[float, float],
    ending_point: Tuple[float, float],
    graph: Optional[nx.MultiDiGraph] = None,
    area_name: str = "paso_del_norte",
    weight: str = "length",
    properties: Optional[Dict[str, Any]] = None,
    interpolate: bool = True
) -> Dict[str, Any]:
    """
    Calculate the optimal path and return as a GeoJSON Feature.

    Args:
        starting_point: Tuple of (longitude, latitude) for the starting location
        ending_point: Tuple of (longitude, latitude) for the ending location
        graph: Optional pre-loaded graph. If None, will load from area_name
        area_name: Name of the area to load graph from (if graph not provided)
        weight: Edge attribute to minimize ('length' or 'travel_time')
        properties: Optional properties to include in the feature
        interpolate: If True, use edge geometries for detailed curves (default: True)

    Returns:
        GeoJSON Feature dictionary with the optimal path
    """
    linestring = get_optimal_path(starting_point, ending_point, graph, area_name, weight, interpolate)

    return {
        "type": "Feature",
        "geometry": linestring,
        "properties": properties or {}
    }
