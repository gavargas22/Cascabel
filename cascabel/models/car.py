from shapely.geometry import Point
import numpy as np
import utm


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
        self.current_state["odometer"] = 0.0

    def get_varianced_value(self, value):
        variance = np.random.uniform(-0.1, 0.1)
        result = value + (value * variance)

        return result

    def report_gps_position(self, waitline):
        new_position = waitline.compute_position_at_distance_from_start(
            self.current_state["odometer"])
        wgs_position = Point(self.convert_utm_to_latlon(new_position, waitline)[::-1])

        return (
            {
                "utm": {
                    "northings": new_position.y,
                    "eastings": new_position.x
                },
                "lat_lon": wgs_position,
                "shapely": new_position
            }
        )

    def move(self, velocity, acceleration, time_interval):
        # calculate the distance
        distance = velocity * time_interval
        self.current_state["odometer"] += distance

    def convert_utm_to_latlon(self, utm_point, waitline):
        latlon = utm.to_latlon(
            utm_point.x, utm_point.y,
            waitline.utm_zone["utm_zone_number"],
            waitline.utm_zone["utm_zone_letter"])

        return latlon

    # def report_position():
    #     state = Point()
    #     return
