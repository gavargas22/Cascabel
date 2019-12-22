import unittest
from shapely.geometry.point import Point
from cascabel.models.waitline import WaitLine
from cascabel.utils.io.geojson_file import open_geojson_file

class WaitLineTest(unittest.TestCase):
    def setUp(self):
        self.waitline = WaitLine("cascabel/paths/jrz2elp/bota.geojson", {"slow": 0.8, "fast": 0.2}) 

    def test_compute_position_at_distance_from_start_is_point(self):
        point = self.waitline.compute_position_at_distance_from_start(100)
        self.assertIsInstance(point, Point)
        
    def test_compute_position_at_distance_from_start_is_correct(self):
        check_coords = list(Point(362589.32700232416, 3515416.15715211).coords)
        coords = list(self.waitline.compute_position_at_distance_from_start(100).coords)
        self.assertEqual(coords, check_coords)
