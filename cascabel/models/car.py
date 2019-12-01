class Car():
    '''
    Car
    ===

    The most fundamental unit of a wait line, the car is the object that
    reports its position to the server, the data reported is then
    used to generate an estimated wait time for all other users on that bridge.
    '''
    def __init__(self, sampling_rate):
        self.sampling_rate = sampling_rate
