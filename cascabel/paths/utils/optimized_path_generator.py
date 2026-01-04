"""
Optimized Path Generator
========================

Generates paths from random starting points to the preferred queue geometry.
Cars approach from one country and join the queue line to cross into the other country.

This is the optimized version that:
- Uses preferred_queue_geometry as the destination
- Caches graphs and queue geometries
- Routes cars to join the queue efficiently
"""

import json
import pickle
import random
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
import networkx as nx
import pandas as pd
from shapely.geometry import LineString, Point
import pyproj

from .path_finding import get_optimal_path


# Path to bounding boxes configuration
BOUNDING_BOXES_PATH = Path(__file__).parent.parent / "bounding_boxes.json"

# Path to country borders pickle
COUNTRY_BORDERS_PATH = Path(__file__).parent / "country_borders.pkl"

# Cache for loaded graphs and configurations
_GRAPH_CACHE: Dict[str, nx.MultiDiGraph] = {}
_CONFIG_CACHE: Dict[str, Dict] = {}
_COUNTRY_BORDERS_CACHE = None


def load_country_borders() -> pd.DataFrame:
    """
    Load country border polygons from pickle file.

    Returns:
        DataFrame with country geometries and ISO codes
    """
    global _COUNTRY_BORDERS_CACHE

    if _COUNTRY_BORDERS_CACHE is not None:
        return _COUNTRY_BORDERS_CACHE

    with open(COUNTRY_BORDERS_PATH, 'rb') as f:
        _COUNTRY_BORDERS_CACHE = pickle.load(f)

    return _COUNTRY_BORDERS_CACHE


def load_crossing_config(crossing_name: str) -> Dict[str, Any]:
    """
    Load and cache configuration for a border crossing.

    Args:
        crossing_name: Name of the crossing

    Returns:
        Dictionary with bounding_box, preferred_queue_geometry, slowdown_zones
    """
    if crossing_name in _CONFIG_CACHE:
        return _CONFIG_CACHE[crossing_name]

    with open(BOUNDING_BOXES_PATH, 'r') as f:
        data = json.load(f)

    if crossing_name not in data:
        raise ValueError(f"Crossing '{crossing_name}' not found in bounding_boxes.json")

    _CONFIG_CACHE[crossing_name] = data[crossing_name]
    return _CONFIG_CACHE[crossing_name]


def get_queue_linestring(crossing_name: str) -> LineString:
    """
    Extract the preferred queue geometry as a Shapely LineString.

    Args:
        crossing_name: Name of the crossing

    Returns:
        Shapely LineString representing the queue path
    """
    config = load_crossing_config(crossing_name)

    queue_geom = config.get("preferred_queue_geometry", {})
    features = queue_geom.get("features", [])

    if not features:
        raise ValueError(f"No preferred_queue_geometry found for {crossing_name}")

    # Get first feature's geometry
    geometry = features[0].get("geometry", {})
    coordinates = geometry.get("coordinates", [])

    if not coordinates:
        raise ValueError(f"No coordinates in preferred_queue_geometry for {crossing_name}")

    return LineString(coordinates)


def get_direction(crossing_name: str) -> str:
    """
    Get the traffic direction for this crossing from configuration.

    Args:
        crossing_name: Name of the crossing

    Returns:
        Direction string (e.g., "mx2usa", "usa2mx")
    """
    config = load_crossing_config(crossing_name)
    queue_geom = config.get("preferred_queue_geometry", {})
    features = queue_geom.get("features", [])

    if features:
        props = features[0].get("properties", {})
        return props.get("direction", "mx2usa")

    return "mx2usa"  # Default


def get_origin_zone(
    crossing_name: str,
    direction: str = "mx2usa"
) -> Tuple[float, float, float, float]:
    """
    Get the origin zone for car spawning based on traffic direction.

    Args:
        crossing_name: Name of the crossing
        direction: Traffic direction ("mx2usa" or "usa2mx")

    Returns:
        Bounding box (west, south, east, north) for origin zone
    """
    config = load_crossing_config(crossing_name)
    bbox = config["bounding_box"]
    west, south, east, north = bbox

    # Split bounding box by latitude (horizontal split)
    center_lat = (south + north) / 2

    if direction == "mx2usa":
        # Mexico to USA: Cars start in southern half
        return (west, south, east, center_lat)
    elif direction == "usa2mx":
        # USA to Mexico: Cars start in northern half
        return (west, center_lat, east, north)
    else:
        # Default to full bounding box
        return tuple(bbox)


def generate_random_point_in_bbox(
    bbox: Tuple[float, float, float, float],
    direction: Optional[str] = None
) -> Tuple[float, float]:
    """
    Generate a random point within a bounding box that's inside the correct country.

    Uses actual country border polygons from OpenStreetMap to validate points.
    If a point falls in the wrong country, it's discarded and a new one is generated.

    Args:
        bbox: (west, south, east, north)
        direction: "mx2usa" or "usa2mx" - validates point is in the origin country

    Returns:
        (longitude, latitude) guaranteed to be inside the correct country
    """
    west, south, east, north = bbox

    if direction is None:
        # No validation - just return a random point
        lon = random.uniform(west, east)
        lat = random.uniform(south, north)
        return (lon, lat)

    # Load country borders
    borders_df = load_country_borders()

    # Map direction to ISO code (origin country)
    iso_code = "MX" if direction == "mx2usa" else "US"

    # Get the country polygon
    country_row = borders_df[borders_df['ISO3166-1:alpha2'] == iso_code]
    if country_row.empty:
        raise ValueError(f"Country polygon not found for ISO code: {iso_code}")

    country_polygon = country_row.iloc[0]['geometry']

    # Keep trying until we find a point inside the country
    max_attempts = 1000  # Prevent infinite loops
    for _ in range(max_attempts):
        lon = random.uniform(west, east)
        lat = random.uniform(south, north)
        point = Point(lon, lat)

        # Check if point is inside the country
        if country_polygon.contains(point):
            return (lon, lat)

    # If we couldn't find a valid point after max attempts, raise an error
    country_name = "Mexico" if iso_code == "MX" else "USA"
    raise RuntimeError(
        f"Could not find a valid point in {country_name} after {max_attempts} attempts. "
        f"The bounding box may not overlap with {country_name}."
    )


def get_booth_location(crossing_name: str) -> Tuple[float, float]:
    """
    Get the booth location from slowdown_zones.

    Args:
        crossing_name: Name of the crossing

    Returns:
        (longitude, latitude) of booth location
    """
    config = load_crossing_config(crossing_name)
    slowdown_zones = config.get("slowdown_zones", [])

    for zone in slowdown_zones:
        if zone.get("type") == "Feature":
            props = zone.get("properties", {})
            if props.get("type") == "booth":
                geometry = zone.get("geometry", {})
                coordinates = geometry.get("coordinates", [])
                if coordinates and len(coordinates) == 2:
                    return tuple(coordinates)

    raise ValueError(f"No booth location found for {crossing_name}")


def get_queue_entry_point(
    crossing_name: str,
    direction: str = "mx2usa"
) -> Tuple[float, float]:
    """
    Get the entry point where cars join the queue.

    Args:
        crossing_name: Name of the crossing
        direction: Traffic direction

    Returns:
        (longitude, latitude) of queue entry point
    """
    queue_line = get_queue_linestring(crossing_name)

    if direction == "mx2usa":
        # Mexico to USA: Join at the end (last point) of queue line
        coords = list(queue_line.coords)
        return coords[-1]
    elif direction == "usa2mx":
        # USA to Mexico: Join at the start (first point) of queue line
        coords = list(queue_line.coords)
        return coords[0]
    else:
        # Default to end point
        coords = list(queue_line.coords)
        return coords[-1]


def load_and_cache_graph(crossing_name: str) -> nx.MultiDiGraph:
    """
    Load and cache OSM graph for a crossing.

    Args:
        crossing_name: Name of the crossing

    Returns:
        NetworkX MultiDiGraph
    """
    if crossing_name in _GRAPH_CACHE:
        return _GRAPH_CACHE[crossing_name]

    from .path_finding import load_graph
    graph = load_graph(crossing_name)
    _GRAPH_CACHE[crossing_name] = graph

    return graph


def generate_approach_path(
    crossing_name: str,
    direction: str = "mx2usa",
    starting_point: Optional[Tuple[float, float]] = None,
    graph: Optional[nx.MultiDiGraph] = None,
    use_booth_as_destination: bool = True
) -> Dict[str, Any]:
    """
    Generate optimal path from origin to destination (booth or queue entry).

    This creates the "approach" path that cars take to reach the border.

    Args:
        crossing_name: Name of the crossing
        direction: Traffic direction ("mx2usa" or "usa2mx")
        starting_point: Optional starting point. If None, random point in origin zone
        graph: Optional pre-loaded graph
        use_booth_as_destination: If True, route directly to booth; if False, route to queue entry

    Returns:
        Dictionary with approach path data:
            - linestring: GeoJSON LineString from start to destination
            - start_point: Starting coordinates
            - destination_point: Booth or queue entry point
            - direction: Traffic direction
    """
    # Load graph if not provided
    if graph is None:
        graph = load_and_cache_graph(crossing_name)

    # Generate random starting point if not provided
    if starting_point is None:
        origin_zone = get_origin_zone(crossing_name, direction)
        starting_point = generate_random_point_in_bbox(origin_zone, direction=direction)

    # Get destination point (booth or queue entry)
    if use_booth_as_destination:
        destination = get_booth_location(crossing_name)
    else:
        destination = get_queue_entry_point(crossing_name, direction)

    # Generate optimal path from start to destination
    linestring = get_optimal_path(
        starting_point=starting_point,
        ending_point=destination,
        graph=graph,
        area_name=crossing_name,
        weight="length",
        interpolate=True
    )

    return {
        "linestring": linestring,
        "start_point": starting_point,
        "destination_point": destination,
        "queue_entry_point": destination,  # Keep for backward compatibility
        "direction": direction,
        "crossing_name": crossing_name
    }


def get_complete_car_path(
    crossing_name: str,
    direction: str = "mx2usa",
    starting_point: Optional[Tuple[float, float]] = None,
    graph: Optional[nx.MultiDiGraph] = None,
    use_booth_as_destination: bool = True
) -> Dict[str, Any]:
    """
    Generate complete path for a car: approach to booth (or approach + queue).

    Args:
        crossing_name: Name of the crossing
        direction: Traffic direction
        starting_point: Optional starting point
        graph: Optional pre-loaded graph
        use_booth_as_destination: If True, route directly to booth (no queue geometry);
                                   if False, use approach + queue geometry

    Returns:
        Dictionary with complete path data:
            - approach_path: Approach LineString (start to destination)
            - combined_linestring: Complete path coordinates
            - start_point: Starting coordinates
            - end_point: Final coordinates (booth)
            - direction: Traffic direction
            - slowdown_zones: Traffic control points
    """
    # Generate approach path (to booth or queue entry based on flag)
    approach = generate_approach_path(crossing_name, direction, starting_point, graph, use_booth_as_destination)

    # Load slowdown zones
    config = load_crossing_config(crossing_name)
    slowdown_zones = config.get("slowdown_zones", [])

    # Get booth location
    booth_coords = get_booth_location(crossing_name)

    if use_booth_as_destination:
        # Direct routing to booth - no queue geometry needed
        approach_coords = approach["linestring"]["coordinates"]
        combined_coords = approach_coords

        return {
            "approach_path": approach["linestring"],
            "queue_path": None,  # No separate queue path
            "combined_linestring": {"type": "LineString", "coordinates": combined_coords},
            "start_point": approach["start_point"],
            "queue_entry_point": booth_coords,  # Same as booth when routing directly
            "end_point": booth_coords,
            "direction": direction,
            "crossing_name": crossing_name,
            "slowdown_zones": slowdown_zones,
            "total_coordinates": len(combined_coords),
            "approach_length": len(approach_coords),
            "queue_length": 0
        }
    else:
        # Original behavior: approach + queue geometry
        queue_line = get_queue_linestring(crossing_name)
        queue_coords = list(queue_line.coords)
        approach_coords = approach["linestring"]["coordinates"]

        # Remove last point of approach if it duplicates first point of queue
        if approach_coords[-1] == queue_coords[0]:
            approach_coords = approach_coords[:-1]

        combined_coords = approach_coords + queue_coords

        return {
            "approach_path": approach["linestring"],
            "queue_path": {"type": "LineString", "coordinates": queue_coords},
            "combined_linestring": {"type": "LineString", "coordinates": combined_coords},
            "start_point": approach["start_point"],
            "queue_entry_point": approach["queue_entry_point"],
            "end_point": booth_coords,
            "direction": direction,
            "crossing_name": crossing_name,
            "slowdown_zones": slowdown_zones,
            "total_coordinates": len(combined_coords),
            "approach_length": len(approach_coords),
            "queue_length": len(queue_coords)
        }


def clear_cache():
    """Clear all cached data."""
    global _GRAPH_CACHE, _CONFIG_CACHE
    _GRAPH_CACHE.clear()
    _CONFIG_CACHE.clear()
