import numpy as np
from shapely.geometry import MultiPoint
import geopandas as gpd
import pdb


class Simulation():
    def __init__(self, waitline, car):
        self.waitline = waitline
        self.car = car
        self.total_distance = self.waitline.destiny['line_length']
        self.total_steps = int(self.total_distance) * self.car.sampling_rate
        self.linear_space_distance = np.linspace(0, self.total_distance,
                                                 self.total_steps)
        self.starting_point = self.waitline\
            .compute_position_at_distance_from_start(0)
        self.location_points = []

    def __call__(self):
        print("executing simulation...")
        for i in range(0, int(self.total_distance)):
            current_location_point = self.waitline.\
                compute_position_at_distance_from_start(i)
            self.location_points.append(current_location_point)

    def generate_point_geojson(self):
        pdb.set_trace()
        output = MultiPoint(self.location_points)
        gdf = gpd.GeoSeries(output)
        gdf.crs = {'init': 'epsg:4326'}

        return gdf
