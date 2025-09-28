"""
Bounding validation utilities for GeoJSON polygons.

Provides functions to check if points are within polygon boundaries
and constrain coordinates to stay within bounds.
"""

from shapely.geometry import Point


def is_point_in_polygon(point, polygon):
    """
    Check if a point is inside or on the boundary of a polygon.

    Args:
        point (shapely.geometry.Point): The point to check
        polygon (shapely.geometry.Polygon): The polygon boundary

    Returns:
        bool: True if point is inside or on boundary, False otherwise
    """
    return polygon.contains(point) or polygon.touches(point)


def constrain_point_to_bounds(point, polygon):
    """
    Constrain a point to be within polygon bounds.

    If the point is already inside, return it unchanged.
    If outside, find the nearest point on the polygon boundary.

    Args:
        point (shapely.geometry.Point): The point to constrain
        polygon (shapely.geometry.Polygon): The polygon boundary

    Returns:
        shapely.geometry.Point: The constrained point
    """
    if is_point_in_polygon(point, polygon):
        return point

    # Find nearest point on polygon boundary
    nearest_point = polygon.exterior.interpolate(polygon.exterior.project(point))

    return nearest_point
