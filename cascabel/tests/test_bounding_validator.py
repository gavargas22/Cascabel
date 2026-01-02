import unittest
from shapely.geometry import Polygon, Point
from cascabel.utils.bounding_validator import (
    is_point_in_polygon,
    constrain_point_to_bounds,
)


class TestBoundingValidator(unittest.TestCase):

    def setUp(self):
        # Create a simple square polygon for testing
        self.polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

    def test_point_inside_polygon(self):
        """Test that points inside polygon return True"""
        point_inside = Point(5, 5)
        self.assertTrue(is_point_in_polygon(point_inside, self.polygon))

    def test_point_outside_polygon(self):
        """Test that points outside polygon return False"""
        point_outside = Point(15, 15)
        self.assertFalse(is_point_in_polygon(point_outside, self.polygon))

    def test_point_on_boundary(self):
        """Test that points on boundary return True (inclusive)"""
        point_on_boundary = Point(5, 0)  # On bottom edge
        self.assertTrue(is_point_in_polygon(point_on_boundary, self.polygon))

    def test_point_at_vertex(self):
        """Test that points at vertices return True"""
        point_at_vertex = Point(0, 0)
        self.assertTrue(is_point_in_polygon(point_at_vertex, self.polygon))

    def test_constrain_point_inside_stays_same(self):
        """Test that constraining a point already inside returns the same point"""
        point_inside = Point(5, 5)
        constrained = constrain_point_to_bounds(point_inside, self.polygon)
        self.assertEqual(constrained, point_inside)

    def test_constrain_point_outside_moves_inside(self):
        """Test that constraining a point outside moves it to boundary"""
        point_outside = Point(15, 15)
        constrained = constrain_point_to_bounds(point_outside, self.polygon)
        self.assertTrue(is_point_in_polygon(constrained, self.polygon))

    def test_performance_requirement(self):
        """Test that point-in-polygon check is fast enough (< 1ms)"""
        import time

        point = Point(5, 5)

        # Time 1000 checks
        start_time = time.time()
        for _ in range(1000):
            is_point_in_polygon(point, self.polygon)
        end_time = time.time()

        total_time = (end_time - start_time) * 1000  # Convert to milliseconds
        avg_time = total_time / 1000

        self.assertLess(
            avg_time, 1.0, f"Average check time {avg_time:.3f}ms exceeds 1ms limit"
        )


if __name__ == "__main__":
    unittest.main()
