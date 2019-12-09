class WaitLine():
    '''
    Wait Line
    =========

    A wait line is an object that contains the possible paths that can be
    taken by a car as it completes a wait time.
    '''
    def __init__(self, location, possible_paths, speed_regime, total_distance):
        self.possible_paths = possible_paths
        self.speed_regime = {
            "slow": 0.2,
            "fast": 0.8
        }
        self.total_distance = total_distance
        self.regime_location = {
            "start_location": 0.0,
            "inflection_location": (self.total_distance *
                                    self.speed_regime['slow']),
            "end_location": self.total_distance
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
