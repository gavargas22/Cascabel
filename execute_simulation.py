from cascabel.models.waitline import WaitLine
from cascabel.models.car import Car
from cascabel.models.simulation import Simulation
from cascabel.utils.io.geojson_file import open_geojson_file
import pdb

# geojson_data = open_geojson_file("cascabel/paths/jrz2elp/bota.geojson")

waitline = WaitLine(geojson_path="cascabel/paths/jrz2elp/bota.geojson",
                    speed_regime={"slow": 0.8, "fast": 0.2},
                    line_length_seed=0.5)

car = Car(sampling_rate=10, initial_state={"t": 0, "s": 0},
          current_state={"t": 0, "s": 0}, idle_time_seed=30,
          transient_time_seed=5)

simulation = Simulation(waitline=waitline, car=car)
simulation()
pdb.set_trace()
print(waitline.compute_position_at_distance_from_start(100))
# coordinates = waitline.get_path_coordinates()
# waitline.sampling_path['features'][0]['geometry']['coordinates']


# The whole idea is the following:
# 1. Initialize a waitline with a path defined by expected geometry of the line.
