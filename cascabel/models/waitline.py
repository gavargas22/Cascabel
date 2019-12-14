from geojson import Muly

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
    def __init__(self, location, sampling_path, speed_regime):
        self.sampling_path = sampling_path
        self.speed_regime = {
            "slow": 0.8,
            "fast": 0.2
        }

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
    
    def generate_samples(self):
