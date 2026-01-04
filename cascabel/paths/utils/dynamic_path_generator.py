"""
Dynamic Path Generator
======================

Generates paths dynamically using optimal routing from random starting points
within bounding boxes to border crossing destinations.

This replaces the old static GeoJSON path system with dynamic path generation
using OpenStreetMap road networks.
"""

import random
import json
import pickle
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import networkx as nx
import pandas as pd
from shapely.geometry import LineString, Point
import pyproj

from .path_finding import get_optimal_path, load_graph
from .graph_retrieval import load_bounding_boxes


# Path to bounding boxes configuration
BOUNDING_BOXES_PATH = Path(__file__).parent.parent / "bounding_boxes.json"

# Path to country borders pickle
COUNTRY_BORDERS_PATH = Path(__file__).parent / "country_borders.pkl"

# Cache for country borders
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
    Load configuration for a specific border crossing.

    Args:
        crossing_name: Name of the crossing (e.g., "paso_del_norte", "bridge_of_the_americas")

    Returns:
        Dictionary containing bounding_box and slowdown_zones
    """
    with open(BOUNDING_BOXES_PATH, 'r') as f:
        data = json.load(f)

    if crossing_name not in data:
        raise ValueError(f"Crossing '{crossing_name}' not found in bounding_boxes.json")

    return data[crossing_name]


def get_country_origin_zones(
    crossing_name: str,
    country: str = "mexico"
) -> Tuple[float, float, float, float]:
    """
    Get the origin zone (sub-bounding box) for starting cars from a specific country.

    Args:
        crossing_name: Name of the border crossing
        country: "mexico" or "usa" - which side cars are coming from

    Returns:
        Tuple of (west, south, east, north) for the origin zone
    """
    config = load_crossing_config(crossing_name)
    bbox = config["bounding_box"]

    # bbox format: [west, south, east, north]
    west, south, east, north = bbox

    # Calculate center latitude to split zones
    center_lat = (south + north) / 2

    if country.lower() == "mexico":
        # Mexico is typically south of the border
        # Use southern portion of bounding box
        return (west, south, east, center_lat)
    elif country.lower() == "usa":
        # USA is typically north of the border
        # Use northern portion of bounding box
        return (west, center_lat, east, north)
    else:
        raise ValueError(f"Invalid country: {country}. Must be 'mexico' or 'usa'")


def generate_random_point_in_bbox(
    bbox: Tuple[float, float, float, float],
    country: Optional[str] = None
) -> Tuple[float, float]:
    """
    Generate a random point within a bounding box that's inside the specified country.

    Uses actual country border polygons from OpenStreetMap to validate points.
    If a point falls in the wrong country, it's discarded and a new one is generated.

    Args:
        bbox: Tuple of (west, south, east, north) in degrees
        country: "mexico" or "usa" - validates point is inside this country's borders

    Returns:
        Tuple of (longitude, latitude) guaranteed to be inside the country
    """
    west, south, east, north = bbox

    if country is None:
        # No validation - just return a random point
        lon = random.uniform(west, east)
        lat = random.uniform(south, north)
        return (lon, lat)

    # Load country borders
    borders_df = load_country_borders()

    # Map country name to ISO code
    iso_code = "MX" if country.lower() == "mexico" else "US"

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
    raise RuntimeError(
        f"Could not find a valid point in {country} after {max_attempts} attempts. "
        f"The bounding box may not overlap with {country}."
    )


def get_booth_location(crossing_name: str) -> Tuple[float, float]:
    """
    Get the booth location from slowdown zones.

    Args:
        crossing_name: Name of the border crossing

    Returns:
        Tuple of (longitude, latitude) for the booth
    """
    config = load_crossing_config(crossing_name)
    slowdown_zones = config.get("slowdown_zones", [])

    # Find the booth zone
    for zone in slowdown_zones:
        if zone.get("properties", {}).get("type") == "booth":
            coords = zone.get("geometry", {}).get("coordinates", [])
            if len(coords) >= 2:
                return (coords[0], coords[1])


def generate_dynamic_path(
    crossing_name: str,
    country: str = "mexico",
    graph: Optional[nx.MultiDiGraph] = None,
    starting_point: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Generate a dynamic path from a random starting point to the border crossing booth.

    Args:
        crossing_name: Name of the border crossing
        country: "mexico" or "usa" - which country cars are coming from
        graph: Optional pre-loaded graph. If None, will load from crossing_name
        starting_point: Optional specific starting point (lon, lat). If None, random point is generated

    Returns:
        Dictionary containing:
            - "linestring": GeoJSON LineString with the path
            - "start_point": (lon, lat) starting coordinates
            - "end_point": (lon, lat) ending coordinates (booth)
            - "slowdown_zones": List of slowdown zones along the path
            - "country_of_origin": Country the car is coming from
    """
    # Load graph if not provided
    if graph is None:
        graph = load_graph(crossing_name)

    # Generate random starting point in country-specific zone if not provided
    if starting_point is None:
        origin_bbox = get_country_origin_zones(crossing_name, country)
        starting_point = generate_random_point_in_bbox(origin_bbox, country=country)

    # Get booth location
    booth_location = get_booth_location(crossing_name)

    # Generate optimal path
    linestring = get_optimal_path(
        starting_point=starting_point,
        ending_point=booth_location,
        graph=graph,
        area_name=crossing_name,
        weight="length",
        interpolate=True
    )

    # Load slowdown zones
    config = load_crossing_config(crossing_name)
    slowdown_zones = config.get("slowdown_zones", [])

    return {
        "linestring": linestring,
        "start_point": starting_point,
        "end_point": booth_location,
        "slowdown_zones": slowdown_zones,
        "country_of_origin": country,
        "crossing_name": crossing_name
    }


def create_linestring_from_coordinates(coordinates: list) -> LineString:
    """
    Create a Shapely LineString from a list of [lon, lat] coordinates.

    Args:
        coordinates: List of [longitude, latitude] pairs

    Returns:
        Shapely LineString object
    """
    return LineString(coordinates)


def convert_linestring_to_utm(linestring: LineString, utm_zone: int = 13) -> LineString:
    """
    Convert a LineString from lat/lon to UTM coordinates.

    Args:
        linestring: Shapely LineString in WGS84 (lon, lat)
        utm_zone: UTM zone number (default: 13 for El Paso/Juarez area)

    Returns:
        Shapely LineString in UTM coordinates
    """
    # Create projection transformer
    # WGS84 to UTM
    wgs84 = pyproj.CRS("EPSG:4326")
    utm = pyproj.CRS(f"EPSG:326{utm_zone:02d}")  # Northern hemisphere UTM

    transformer = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True)

    # Transform all coordinates
    utm_coords = [transformer.transform(x, y) for x, y in linestring.coords]

    return LineString(utm_coords)


def get_slowdown_zones_on_path(
    linestring: LineString,
    slowdown_zones: list,
    utm_zone: int = 13
) -> list:
    """
    Calculate positions of slowdown zones along a path.

    Args:
        linestring: The path LineString in UTM coordinates
        slowdown_zones: List of slowdown zone features from bounding_boxes.json
        utm_zone: UTM zone number

    Returns:
        List of slowdown zones with calculated position_meters along the path
    """
    result = []

    # Create projection transformer
    wgs84 = pyproj.CRS("EPSG:4326")
    utm = pyproj.CRS(f"EPSG:326{utm_zone:02d}")
    transformer = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True)

    for zone in slowdown_zones:
        props = zone.get("properties", {})
        geom = zone.get("geometry", {})
        coords = geom.get("coordinates", [])

        if len(coords) < 2:
            continue

        # Convert zone point to UTM
        zone_utm_x, zone_utm_y = transformer.transform(coords[0], coords[1])
        zone_point = Point(zone_utm_x, zone_utm_y)

        # Project point onto linestring to get position
        position_meters = linestring.project(zone_point)

        # Build zone info
        zone_info = {
            "type": props.get("type"),
            "name": props.get("name", "Unknown"),
            "description": props.get("description", ""),
            "position_meters": position_meters,
            "coordinates": coords
        }

        # Add type-specific properties
        if props.get("type") == "slowdown":
            zone_info["target_speed_mps"] = props.get("target_speed_mps", 1.34)
            zone_info["slowdown_distance_meters"] = 30
        elif props.get("type") == "booth":
            zone_info["stop_distance_meters"] = 20
            zone_info["queue_start_meters"] = position_meters - 20

        result.append(zone_info)

    return result
