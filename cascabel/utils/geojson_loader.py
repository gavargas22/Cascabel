import json
import utm
from shapely.geometry import Polygon, Point
import pyproj


class GeoJSONLoader:
    """
    Loads and parses GeoJSON files containing border crossing boundaries.

    Expected GeoJSON structure:
    - FeatureCollection with features for polygon and points
    - Polygon feature with properties.object_type = "coordinate_container"
    - Point features with properties.location = "start" and "stop"
    - Top-level properties.utm_epsg_code for UTM zone
    """

    def __init__(self, geojson_path):
        """
        Initialize GeoJSON loader.

        Args:
            geojson_path (str): Path to the GeoJSON file

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            ValueError: If required features or properties are missing
        """
        with open(geojson_path, "r") as f:
            self.data = json.load(f)

        self._validate_geojson_structure()
        self._extract_components()

    def _validate_geojson_structure(self):
        """Validate that the GeoJSON has the required structure."""
        if (
            not isinstance(self.data, dict)
            or self.data.get("type") != "FeatureCollection"
        ):
            raise ValueError("GeoJSON must be a FeatureCollection")

        features = self.data.get("features", [])
        if not features:
            raise ValueError("GeoJSON must contain at least one feature")

        properties = self.data.get("properties", {})
        if "utm_epsg_code" not in properties:
            raise ValueError("GeoJSON properties must contain utm_epsg_code")

    def _extract_components(self):
        """Extract polygon, start/stop points, and UTM code from features."""
        features = self.data["features"]
        properties = self.data["properties"]

        # Extract polygon
        polygon_features = [
            f
            for f in features
            if f.get("properties", {}).get("object_type") == "coordinate_container"
        ]
        if not polygon_features:
            raise ValueError(
                "No polygon feature found with " "object_type='coordinate_container'"
            )
        if len(polygon_features) > 1:
            raise ValueError("Multiple polygon features found, " "expected exactly one")

        polygon_coords = polygon_features[0]["geometry"]["coordinates"][0]
        self.polygon = Polygon(polygon_coords)

        # Extract start point
        start_features = [
            f for f in features if f.get("properties", {}).get("location") == "start"
        ]
        if not start_features:
            raise ValueError("No start point found with location='start'")
        if len(start_features) > 1:
            raise ValueError("Multiple start points found, " "expected exactly one")

        start_coords = start_features[0]["geometry"]["coordinates"]
        self.start_point = Point(start_coords)

        # Extract stop point
        stop_features = [
            f for f in features if f.get("properties", {}).get("location") == "stop"
        ]
        if not stop_features:
            raise ValueError("No stop point found with location='stop'")
        if len(stop_features) > 1:
            raise ValueError("Multiple stop points found, " "expected exactly one")

        stop_coords = stop_features[0]["geometry"]["coordinates"]
        self.stop_point = Point(stop_coords)

        # Extract UTM EPSG code
        self.utm_epsg_code = properties["utm_epsg_code"]

        # Determine UTM zone from coordinates
        self._determine_utm_zone()

        # Transform geometries to UTM
        self._transform_to_utm()

    def _determine_utm_zone(self):
        """Determine UTM zone from polygon coordinates using utm package."""
        # Use centroid of polygon to determine zone
        centroid = self.polygon.centroid
        easting, northing, zone_number, zone_letter = utm.from_latlon(
            centroid.y, centroid.x
        )
        self.utm_zone = {"number": zone_number, "letter": zone_letter}

        # Validate against provided EPSG code
        expected_epsg = 32600 + zone_number  # UTM north zones
        if zone_letter == "S":
            expected_epsg = 32700 + zone_number  # UTM south zones

        if self.utm_epsg_code != expected_epsg:
            raise ValueError(
                f"GeoJSON utm_epsg_code {self.utm_epsg_code} "
                f"does not match calculated UTM zone EPSG "
                f"{expected_epsg}"
            )

    def _transform_to_utm(self):
        """Transform all geometries to UTM coordinates."""
        # Create transformation function
        wgs84 = pyproj.CRS("EPSG:4326")
        utm_crs = pyproj.CRS(f"EPSG:{self.utm_epsg_code}")
        transformer = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True)

        # Transform polygon coordinates
        utm_coords = []
        for coord in self.polygon.exterior.coords:
            x, y = transformer.transform(coord[0], coord[1])
            utm_coords.append((x, y))
        self.polygon_utm = Polygon(utm_coords)

        # Transform start point
        x, y = transformer.transform(self.start_point.x, self.start_point.y)
        self.start_point_utm = Point(x, y)

        # Transform stop point
        x, y = transformer.transform(self.stop_point.x, self.stop_point.y)
        self.stop_point_utm = Point(x, y)

    def latlon_to_utm(self, lat, lon):
        """
        Convert latitude/longitude to UTM coordinates.

        Args:
            lat (float): Latitude
            lon (float): Longitude

        Returns:
            tuple: UTM coordinates (easting, northing,
                    zone_number, zone_letter)
        """
        return utm.from_latlon(lat, lon)

    def utm_to_latlon(self, easting, northing, zone_number, zone_letter):
        """
        Convert UTM coordinates to latitude/longitude.

        Args:
            easting (float): UTM easting
            northing (float): UTM northing
            zone_number (int): UTM zone number
            zone_letter (str): UTM zone letter

        Returns:
            tuple: (longitude, latitude)
        """
        return utm.to_latlon(easting, northing, zone_number, zone_letter)
