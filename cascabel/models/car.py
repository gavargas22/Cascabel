from shapely.geometry import Point
import numpy as np


class Car():
    '''
    Car
    ===

    The most fundamental unit of a wait line, the car is the object that
    reports its position to the server, the data reported is then
    used to generate an estimated wait time for all other users on that bridge.
    '''
    def __init__(self, sampling_rate, initial_state, current_state,
                 idle_time_seed, transient_time_seed):
        self.sampling_rate = sampling_rate
        # Movement parameters
        self.max_velocity_seed = 20
        self.min_velocity_seed = 10
        self.current_state = initial_state
        self.initial_state = initial_state

    def get_varianced_value(self, value):
        variance = np.random.uniform(-0.1, 0.1)
        result = value + (value * variance)

        return result

    def insert_car_in_simulation(waitline):
        pass

    # def report_position():
    #     state = Point()
    #     return
