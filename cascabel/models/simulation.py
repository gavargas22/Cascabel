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
            "running": False,
            "time_factor": 1  # 1 mean seconds, 1000 means milliseconds
        }

        self.temporal_state = {
            "previous_simulation_time": 0,
            "simulation_time": 0,
        }

        self.regime_parameters = self.waitline.compute_regime_locations

    def __call__(self):
        print("executing simulation...")
        self.simulation_state["running"] = True
        while self.simulation_state["running"]:
            # Start the time from 0 to n which is the time end
            # The simulation is running
            # Advance time one incremental unit
            self.advance_time()
            # Perform all the checks and calculations of movement
            # Check if we are still within the wait line
            if self.still_in_waitline:
                # If we are in the wait line the continue passage of time
                print("Continuing simulation")
                # Move the car based on time interval and speed
                self.car.move(velocity=10, acceleration=0,
                              time_interval=self.compute_time_delta())
            else:
                # Otherwise stop simulation
                self.simulation_state["running"] = False

            # Set a record of the previous timestamp
            self.temporal_state["previous_simulation_time"] = \
                self.temporal_state["simulation_time"]

        # Get the regime that we are in
        # If we are in the fast regime, then we do not stop
        # If we are in the slow moving regime then we stop at uniform
        # intervals

    def generate_point_geojson(self):
        pdb.set_trace()
        output = MultiPoint(self.location_points)
        gdf = gpd.GeoSeries(output)
        gdf.crs = {'init': 'epsg:4326'}

        return gdf

    def compute_time_delta(self):
        '''
        Compute time delta
        ------------------

        A function that calculates the elapsed times between simulation frames
        '''
        initial = self.temporal_state["previous_simulation_time"]
        final = self.temporal_state["simulation_time"]
        time_delta = final-initial

        return time_delta

    def still_in_waitline(self):
        return True

    def simulate_state_at(self):
        '''
        Function that calculates the conditions at a given tiemstamp
        '''
        return "Continuing"

    def advance_time(self):
        '''
        Arrow of time function
        ========================

        A function that continues the progression of time as in the real world
        '''
        delta_t_amount = self.simulation_state["time_factor"] / 1
        self.temporal_state["simulation_time"] += delta_t_amount
        # self.temporal_state["previous_simulation_time"] += (delta_t_amount)
