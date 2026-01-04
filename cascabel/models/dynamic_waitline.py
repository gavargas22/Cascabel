"""
Dynamic Wait Line
=================

A wait line that uses dynamically generated paths from random starting points
to border crossing destinations, replacing the old static GeoJSON-based system.
"""

import numpy as np
import pyproj
from shapely.geometry import LineString, Point
from typing import Dict, Any, Optional, Tuple
import networkx as nx

from cascabel.paths.utils.dynamic_path_generator import (
    generate_dynamic_path,
    convert_linestring_to_utm,
    get_slowdown_zones_on_path,
    create_linestring_from_coordinates
)


class DynamicWaitLine:
    """
    Dynamic Wait Line using optimal path routing.

    This replaces the old WaitLine class that used static GeoJSON files.
    Instead, it generates paths dynamically using OpenStreetMap road networks.
    """

    def __init__(
        self,
        crossing_name: str,
        country: str = "mexico",
        graph: Optional[nx.MultiDiGraph] = None,
        starting_point: Optional[Tuple[float, float]] = None,
        line_length_seed: float = 1.0,
        utm_zone: int = 13
    ):
        """
        Initialize a dynamic wait line with an optimal path.

        Args:
            crossing_name: Name of the border crossing (e.g., "paso_del_norte")
            country: "mexico" or "usa" - which country cars are coming from
            graph: Optional pre-loaded OSM graph
            starting_point: Optional specific starting point (lon, lat). If None, random point is generated
            line_length_seed: Multiplier for line length (default: 1.0)
            utm_zone: UTM zone number (default: 13 for El Paso/Juarez)
        """
        self.crossing_name = crossing_name
        self.country = country
        self.utm_zone = utm_zone
        self.line_length_seed = line_length_seed

        # Generate dynamic path
        path_data = generate_dynamic_path(
            crossing_name=crossing_name,
            country=country,
            graph=graph,
            starting_point=starting_point
        )

        # Store path information
        self.linestring_geojson = path_data["linestring"]
        self.start_point = path_data["start_point"]
        self.end_point = path_data["end_point"]
        self.slowdown_zones_raw = path_data["slowdown_zones"]
        self.country_of_origin = path_data["country_of_origin"]

        # Create Shapely LineString from coordinates
        coordinates = self.linestring_geojson["coordinates"]
        self.linestring_latlon = create_linestring_from_coordinates(coordinates)

        # Convert to UTM for distance calculations
        self.utm_linestring = convert_linestring_to_utm(self.linestring_latlon, utm_zone)
        self.waitline_length = self.utm_linestring.length

        # Setup projector for coordinate conversions
        self.projector = pyproj.Proj(f"EPSG:326{utm_zone:02d}")

        # Calculate destiny (journey end point)
        self.destiny = {
            "line_length": self.waitline_length * line_length_seed,
            "wait_time": 2700,  # Legacy parameter
            "officer_wait_factor": np.random.uniform(-0.1, 0.1),
        }

        # Speed regime parameters (compatible with old system)
        self.speed_regime = {"slow": 0.8, "fast": 0.2}
        self.regime_parameters = self.compute_regime_locations()

        # Process slowdown zones and calculate their positions on the path
        self.traffic_control_points = get_slowdown_zones_on_path(
            self.utm_linestring,
            self.slowdown_zones_raw,
            utm_zone
        )

        # Store UTM zone info for compatibility
        self.utm_zone_dict = {"utm_zone_number": utm_zone, "utm_zone_letter": "S"}

    def compute_regime_locations(self) -> Dict[str, float]:
        """
        Compute distance-based regime locations (compatible with old WaitLine).

        Returns:
            Dictionary with start, inflection, and end locations
        """
        return {
            "start_location": 0.0,
            "inflection_location": self.destiny["line_length"] * self.speed_regime["slow"],
            "end_location": self.destiny["line_length"],
        }

    def compute_position_at_distance_from_start(self, distance_from_start: float) -> Point:
        """
        Get the position along the path at a given distance from the start.

        Args:
            distance_from_start: Distance in meters from the start of the path

        Returns:
            Shapely Point in UTM coordinates
        """
        # Clamp distance to valid range
        distance_from_start = max(0, min(distance_from_start, self.waitline_length))

        # Interpolate point along the UTM linestring
        point_utm = self.utm_linestring.interpolate(distance_from_start)

        return point_utm

    def utm_to_latlon(self, utm_point: Point) -> list:
        """
        Convert UTM point to latitude/longitude coordinates.

        Args:
            utm_point: Shapely Point in UTM coordinates

        Returns:
            List [longitude, latitude]
        """
        lon, lat = self.projector(utm_point.x, utm_point.y, inverse=True)
        return [lon, lat]

    def get_path_geojson(self) -> Dict[str, Any]:
        """
        Get the complete path as a GeoJSON Feature.

        Returns:
            GeoJSON Feature with LineString geometry
        """
        return {
            "type": "Feature",
            "geometry": self.linestring_geojson,
            "properties": {
                "crossing_name": self.crossing_name,
                "country_of_origin": self.country_of_origin,
                "path_length_meters": self.waitline_length,
                "start_point": self.start_point,
                "end_point": self.end_point,
            }
        }

    def __repr__(self):
        return (
            f"DynamicWaitLine(crossing={self.crossing_name}, "
            f"country={self.country}, length={self.waitline_length:.1f}m)"
        )
