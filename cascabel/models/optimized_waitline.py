"""
Optimized Dynamic Wait Line
============================

Uses the new optimized path generation system that combines:
1. Approach path from random origin to queue entry point
2. Preferred queue geometry from bounding_boxes.json

This is more efficient and uses the actual queue structure.
"""

import numpy as np
import pyproj
from shapely.geometry import LineString, Point
from typing import Dict, Any, Optional, Tuple, List
import networkx as nx

from cascabel.paths.utils.optimized_path_generator import (
    get_complete_car_path,
    load_and_cache_graph,
    get_queue_linestring,
    load_crossing_config
)


class OptimizedWaitLine:
    """
    Optimized Wait Line using approach path + queue geometry.

    Each car gets:
    1. Random starting point in origin zone
    2. Optimal approach path to queue entry
    3. Shared queue geometry (preferred_queue_geometry)
    """

    def __init__(
        self,
        crossing_name: str,
        direction: str = "mx2usa",
        graph: Optional[nx.MultiDiGraph] = None,
        starting_point: Optional[Tuple[float, float]] = None,
        utm_zone: int = 13
    ):
        """
        Initialize optimized wait line.

        Args:
            crossing_name: Name of the crossing (e.g., "paso_del_norte")
            direction: Traffic direction ("mx2usa" or "usa2mx")
            graph: Optional pre-loaded OSM graph (will be cached if None)
            starting_point: Optional specific starting point
            utm_zone: UTM zone number (default: 13 for El Paso/Juarez)
        """
        self.crossing_name = crossing_name
        self.direction = direction
        self.utm_zone = utm_zone

        # Load or use cached graph
        if graph is None:
            graph = load_and_cache_graph(crossing_name)
        self.graph = graph

        # Generate complete car path (route directly to booth, no queue geometry)
        path_data = get_complete_car_path(
            crossing_name=crossing_name,
            direction=direction,
            starting_point=starting_point,
            graph=graph,
            use_booth_as_destination=True  # Route directly to booth
        )

        # Store path components
        self.approach_path_geojson = path_data["approach_path"]
        self.queue_path_geojson = path_data["queue_path"]
        self.combined_linestring_geojson = path_data["combined_linestring"]

        self.start_point = path_data["start_point"]
        self.queue_entry_point = path_data["queue_entry_point"]
        self.end_point = path_data["end_point"]
        self.slowdown_zones_raw = path_data["slowdown_zones"]

        # Setup projector for coordinate conversions (must come before UTM conversions)
        self.projector = pyproj.Proj(f"EPSG:326{utm_zone:02d}")

        # Create Shapely LineStrings
        coords = self.combined_linestring_geojson["coordinates"]
        self.linestring_latlon = LineString(coords)

        # Convert to UTM for distance calculations
        self.utm_linestring = self._convert_to_utm(self.linestring_latlon)
        self.waitline_length = self.utm_linestring.length

        # Calculate approach and queue segment lengths in UTM
        approach_coords = self.approach_path_geojson["coordinates"]

        # Handle case where queue_path is None (routing directly to booth)
        if self.queue_path_geojson is not None:
            queue_coords = self.queue_path_geojson["coordinates"]
            self.queue_linestring = self._convert_to_utm(LineString(queue_coords))
            self.queue_length_meters = self.queue_linestring.length
        else:
            # No queue geometry - entire path is approach
            queue_coords = []
            self.queue_linestring = None
            self.queue_length_meters = 0.0

        self.approach_linestring = self._convert_to_utm(LineString(approach_coords))
        self.approach_length_meters = self.approach_linestring.length

        # Journey parameters
        self.destiny = {
            "line_length": self.waitline_length,
            "approach_length": self.approach_length_meters,
            "queue_length": self.queue_length_meters,
            "wait_time": 2700,
            "officer_wait_factor": np.random.uniform(-0.1, 0.1),
        }

        # Speed regime (for compatibility)
        self.speed_regime = {"slow": 0.8, "fast": 0.2}
        self.regime_parameters = self.compute_regime_locations()

        # Process traffic control points
        self.traffic_control_points = self._process_slowdown_zones()

        # UTM zone info
        self.utm_zone_dict = {"utm_zone_number": utm_zone, "utm_zone_letter": "S"}

    def _convert_to_utm(self, linestring: LineString) -> LineString:
        """Convert LineString from lat/lon to UTM."""
        utm_coords = []
        for lon, lat in linestring.coords:
            x, y = self.projector(lon, lat)
            utm_coords.append((x, y))
        return LineString(utm_coords)

    def interpolate(self, position: float):
        """
        Get point on path at given position (in meters).

        Args:
            position: Distance along path in meters

        Returns:
            Shapely Point in lat/lon coordinates
        """
        # Use UTM linestring for accurate distance-based interpolation
        utm_point = self.utm_linestring.interpolate(position)

        # Convert back to lat/lon using inverse projection
        lon, lat = self.projector(utm_point.x, utm_point.y, inverse=True)

        from shapely.geometry import Point
        return Point(lon, lat)

    def _process_slowdown_zones(self) -> List[Dict[str, Any]]:
        """Calculate positions of slowdown zones along the path."""
        zones = []

        for zone_feature in self.slowdown_zones_raw:
            props = zone_feature.get("properties", {})
            geom = zone_feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            if len(coords) < 2:
                continue

            # Convert zone point to UTM
            zone_x, zone_y = self.projector(coords[0], coords[1])
            zone_point = Point(zone_x, zone_y)

            # Project point onto linestring
            position_meters = self.utm_linestring.project(zone_point)

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
                zone_info["stop_distance_meters"] = 40
                zone_info["queue_start_meters"] = position_meters - 40

            zones.append(zone_info)

        return zones

    def compute_regime_locations(self) -> Dict[str, float]:
        """Compute distance-based regime locations."""
        return {
            "start_location": 0.0,
            "inflection_location": self.destiny["line_length"] * self.speed_regime["slow"],
            "end_location": self.destiny["line_length"],
        }

    def compute_position_at_distance_from_start(self, distance_from_start: float) -> Point:
        """
        Get position along path at given distance.

        Args:
            distance_from_start: Distance in meters from start

        Returns:
            Shapely Point in UTM coordinates
        """
        distance_from_start = max(0, min(distance_from_start, self.waitline_length))
        return self.utm_linestring.interpolate(distance_from_start)

    def utm_to_latlon(self, utm_point: Point) -> List[float]:
        """
        Convert UTM point to lat/lon.

        Args:
            utm_point: Shapely Point in UTM

        Returns:
            [longitude, latitude]
        """
        lon, lat = self.projector(utm_point.x, utm_point.y, inverse=True)
        return [lon, lat]

    def is_in_queue_segment(self, distance_from_start: float) -> bool:
        """
        Check if position is in the queue segment (vs approach segment).

        Args:
            distance_from_start: Distance in meters from start

        Returns:
            True if in queue segment, False if in approach segment
        """
        return distance_from_start >= self.approach_length_meters

    def get_path_geojson(self) -> Dict[str, Any]:
        """Get complete path as GeoJSON Feature."""
        return {
            "type": "Feature",
            "geometry": self.combined_linestring_geojson,
            "properties": {
                "crossing_name": self.crossing_name,
                "direction": self.direction,
                "total_length_meters": self.waitline_length,
                "approach_length_meters": self.approach_length_meters,
                "queue_length_meters": self.queue_length_meters,
                "start_point": self.start_point,
                "queue_entry_point": self.queue_entry_point,
                "end_point": self.end_point,
            }
        }

    def __repr__(self):
        return (
            f"OptimizedWaitLine(crossing={self.crossing_name}, "
            f"direction={self.direction}, "
            f"length={self.waitline_length:.1f}m, "
            f"approach={self.approach_length_meters:.1f}m, "
            f"queue={self.queue_length_meters:.1f}m)"
        )
