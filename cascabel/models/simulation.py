import numpy as np
from shapely.geometry import MultiPoint, LineString, Point
import geopandas as gpd
import pdb


class Simulation():
    '''
    Simulation Model
    ----------------
    
    This is the model that describes how the simulation
    '''
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
        
        self.regime_parameters = self.waitline.compute_regime_locations

    def __call__(self):
        print("executing simulation...")
        
        self.simulation_state["running"] = True
        while self.simulation_state["running"]:
            # Start the time from 0 to n which is the time end
            # Check if we are still within the wait line
            if self.still_in_waitline:
                # If we are in the wait line the continue
                print("Continuing simulation")
                pdb.set_trace()
                regime_at_location = self.waitline.regime_parameters
            else:
                # Otherwise stop simulation
                self.simulation_state["running"] = False

        #    Get the regime that we are in
        #    If we are in the fast regime, then we do not stop
        #    If we are in the slow moving regime then we stop at uniform intervals
        
        
        # for i in range(0, int(self.total_distance)):
        #     current_location_point = self.waitline.\
        #         compute_position_at_distance_from_start(i)
        #     self.location_points.append(current_location_point)

    def generate_point_geojson(self):
        pdb.set_trace()
        output = MultiPoint(self.location_points)
        gdf = gpd.GeoSeries(output)
        gdf.crs = {'init': 'epsg:4326'}

        return gdf
    
    def still_in_waitline(self):
        return True

    def simulate_state_at(self):
        '''
        Function that calculates the conditions at a given tiemstamp
        '''
        return "Continuing"
