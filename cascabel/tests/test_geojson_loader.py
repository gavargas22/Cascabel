import unittest
import json
import tempfile
import os
from cascabel.utils.geojson_loader import GeoJSONLoader


class TestGeoJSONLoader(unittest.TestCase):

    def setUp(self):
        # Create a temporary valid GeoJSON file for testing
        self.valid_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "test_bridge",
                        "object_type": "coordinate_container",
                        "direction": "mx2usa",
                    },
                    "geometry": {
                        "coordinates": [
                            [
                                [-106.45, 31.74],
                                [-106.46, 31.75],
                                [-106.47, 31.76],
                                [-106.45, 31.74],
                            ]
                        ],
                        "type": "Polygon",
                    },
                    "id": 0,
                },
                {
                    "type": "Feature",
                    "properties": {"location": "start"},
                    "geometry": {"coordinates": [-106.452, 31.748], "type": "Point"},
                },
                {
                    "type": "Feature",
                    "properties": {"location": "stop"},
                    "geometry": {"coordinates": [-106.451, 31.767], "type": "Point"},
                },
            ],
            "properties": {"name": "Test Bridge", "utm_epsg_code": 32613},
        }

    def test_load_valid_geojson(self):
        """Test loading a valid GeoJSON file with polygon and points"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(self.valid_geojson, f)
            temp_path = f.name

        try:
            loader = GeoJSONLoader(temp_path)
            self.assertIsNotNone(loader.polygon)
            self.assertIsNotNone(loader.start_point)
            self.assertIsNotNone(loader.stop_point)
            self.assertEqual(loader.utm_epsg_code, 32613)
            # Check UTM versions exist
            self.assertIsNotNone(loader.polygon_utm)
            self.assertIsNotNone(loader.start_point_utm)
            self.assertIsNotNone(loader.stop_point_utm)
            self.assertIsNotNone(loader.utm_zone)
        finally:
            os.unlink(temp_path)

    def test_missing_polygon_raises_error(self):
        """Test that missing polygon feature raises ValueError"""
        invalid_geojson = self.valid_geojson.copy()
        invalid_geojson["features"] = [
            f
            for f in invalid_geojson["features"]
            if f.get("properties", {}).get("object_type") != "coordinate_container"
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(invalid_geojson, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                GeoJSONLoader(temp_path)
        finally:
            os.unlink(temp_path)

    def test_missing_start_point_raises_error(self):
        """Test that missing start point raises ValueError"""
        invalid_geojson = self.valid_geojson.copy()
        invalid_geojson["features"] = [
            f
            for f in invalid_geojson["features"]
            if f.get("properties", {}).get("location") != "start"
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(invalid_geojson, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                GeoJSONLoader(temp_path)
        finally:
            os.unlink(temp_path)

    def test_missing_stop_point_raises_error(self):
        """Test that missing stop point raises ValueError"""
        invalid_geojson = self.valid_geojson.copy()
        invalid_geojson["features"] = [
            f
            for f in invalid_geojson["features"]
            if f.get("properties", {}).get("location") != "stop"
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(invalid_geojson, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                GeoJSONLoader(temp_path)
        finally:
            os.unlink(temp_path)

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with self.assertRaises(json.JSONDecodeError):
                GeoJSONLoader(temp_path)
        finally:
            os.unlink(temp_path)

    def test_missing_utm_epsg_code_raises_error(self):
        """Test that missing utm_epsg_code in properties raises ValueError"""
        invalid_geojson = self.valid_geojson.copy()
        del invalid_geojson["properties"]["utm_epsg_code"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(invalid_geojson, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                GeoJSONLoader(temp_path)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
