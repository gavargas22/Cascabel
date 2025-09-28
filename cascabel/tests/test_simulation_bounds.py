import unittest
from cascabel.models.simulation import Simulation
from cascabel.models.waitline import WaitLine
from cascabel.models.models import BorderCrossingConfig
from shapely.geometry import Polygon


class TestSimulationBounds(unittest.TestCase):

    def setUp(self):
        # Create test GeoJSON
        self.test_geojson = {
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

    def test_simulation_positions_within_bounds(self):
        """Test that all simulation positions are within bounding polygon"""
        # Use existing pdn.geojson for waitline (has LineString)
        geojson_path = "cascabel/paths/mx2usa/pdn.geojson"

        # Create a large bounding polygon that contains the path
        bounds_polygon = Polygon(
            [
                (-106.5, 31.74),
                (-106.4, 31.74),
                (-106.4, 31.76),
                (-106.5, 31.76),
                (-106.5, 31.74),
            ]
        )

        # Create waitline
        waitline = WaitLine(geojson_path, {"slow": 0.8, "fast": 0.2}, 1.0)

        # Create simulation with bounds
        border_config = BorderCrossingConfig(
            num_queues=1,
            nodes_per_queue=[1],
            arrival_rate=1.0,
            service_rates=[2.0],
            safe_distance=10.0,
            max_queue_length=50,
        )

        simulation = Simulation(waitline, border_config, bounds_polygon=bounds_polygon)

        # Run simulation briefly by calling it
        simulation()

        # Check all recorded positions are within bounds
        from cascabel.utils.bounding_validator import is_point_in_polygon

        for point in simulation.location_points:
            self.assertTrue(
                is_point_in_polygon(point, bounds_polygon),
                f"Point {point} is outside bounds",
            )


if __name__ == "__main__":
    unittest.main()
