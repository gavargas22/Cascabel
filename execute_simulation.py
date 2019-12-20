from cascabel.models.waitline import WaitLine
from cascabel.utils.io.geojson_file import open_geojson_file
import pdb

# geojson_data = open_geojson_file("cascabel/paths/jrz2elp/bota.geojson")

waitline = WaitLine("cascabel/paths/jrz2elp/bota.geojson",
                    {"slow": 0.8, "fast": 0.2})
pdb.set_trace()


print(waitline.compute_position_at_distance_from_start(100))
# coordinates = waitline.get_path_coordinates()
# waitline.sampling_path['features'][0]['geometry']['coordinates']


# The whole idea is the following:
# 1. Initialize a waitline with a path defined by expected geometry of the line.
