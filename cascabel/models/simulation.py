class Simulation():
    def __init__(self, waitline, car):
        self.waitline = waitline
        self.car = car

    def __call__(self):
        print("executing simulation...")
