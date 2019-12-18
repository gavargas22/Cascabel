from geojson import loads
from geojson.utils import coords
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import utm
import pyproj
import pdb


class WaitLine():
    '''
    Wait Line
    =========

    A wait line is an object that contains a chosen path that a car
    takes in a certain amount of time from start to finish.

    Properties

    Speed Regime

    A complete wait line behavior has two speed regimes, one is when the person
    has entered the vicinity of the wait line, but has not started waitin
    in the queue, the reporting speed will be higher than 10 m/s.
    The other regime is when the speed is slow and moving along the path at a
    slow speed, this implies that the car is reporting behavior of a queuing
    vehicle.
    '''

    def __init__(self, geojson_path, speed_regime):
        # self.sampling_path = self.decode_geojson_string(geojson_string)
        self.geojson_string = self.decode_geojson_string(geojson_path)
        self.speed_regime = speed_regime
        self.coordinates = self.get_coordinates()
        self.utm_zone = self.get_utm_zone()
        self.utm_coordinates = self.get_utm_coordinates()
        self.utm_linestring = self.get_utm_linestring()
        self.destiny = {
            "line_length": 500,
            "wait_time": 2700
        }

    def decode_geojson_string(self, geojson_path):
        return gpd.read_file(geojson_path)

    def compute_regime_locations(self):
        '''
        A function that computes the distance at which the
        lane starts, changes to a different regime, and
        ends.
        '''
        regime_location = {
            "start_location": 0.0,
            "inflection_location": 0.0,
            "end_location": 0.0
        }

        regime_location['start_location'] = 0.0
        regime_location['inflection_location'] = self.total_distance * \
            self.speed_regime["slow"]

    def get_coordinates(self):
        coordinates = pd.DataFrame(self.geojson_string.iloc[0].geometry.coords)

        return(coordinates)

    def get_utm_coordinates(self):
        '''
        A function that reprojects decimal degree lat and long into
        UTM northings, and eastings.
        '''
        P = pyproj.Proj(
            "+proj=utm +zone=13R, +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
        geo_data = self.geojson_string

        utm_coordinates = self.coordinates.apply(lambda x: P(
            x[0], x[1]), axis=1, result_type='expand')

        return utm_coordinates

    def get_utm_linestring(self):
        linestring = LineString(coordinates=self.utm_coordinates.values)
        result = gpd.GeoDataFrame([linestring])
        return(linestring)

    def get_utm_zone(self):
        '''
        A function that computes the UTM coordinates, and zone for the median
        location of the dataset we are looking at
        '''
        median = self.coordinates.median()
        easting, northing, utm_zone_number, \
            utm_zone_letter = utm.from_latlon(median[1], median[0])

        return (
            {
                "utm_zone_number": utm_zone_number,
                "utm_zone_letter": utm_zone_letter
            }
        )
