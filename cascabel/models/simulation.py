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
        
        self.simulation_state = {
            "running": False
        }
        
        self.temporal_state ={
            "simulation_time": 0,
            "time_factor": 1  # 1 mean seconds, 1000 means milliseconds
        }

    def __call__(self):
        print("executing simulation...")
        
        self.running = True
        while self.simulation_state["running"]:
            
        # Start the time from 0 to n which is the time end
        # Check if we are still within the wait line
        # If we are in the wait line the continue
        # Otherwise stop simulation
        #    Get the regime that we are in
        #    If we are in the fast regime, then we do not stop
        #    If we are in the slow moving regime then we stop at uniform intervals
        self.simulate_state()
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
    
    def still_in_waitline(self):
        return True
    
    def get_regime_parameters(self):
        regime = self.waitline.regime
