from geojson import loads
from geojson.utils import coords
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import utm
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
        self.sampling_path = self.decode_geojson_string(geojson_path)
        self.speed_regime = speed_regime
        self.coordinates = self.get_dataframe()

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

    def get_dataframe(self):
        pdb.set_trace()
        coordinates = pd.DataFrame(self.sampling_path.geometry[0].coords)

        return(coordinates)

    def get_utm_coordinates(self):
        pass

    def get_utm_zone(self):
        coordsself.get_path_coordinates()
