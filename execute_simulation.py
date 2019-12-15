from cascabel.models.waitline import WaitLine
from cascabel.utils.io.geojson_file import open_geojson_file
import pdb

# geojson_data = open_geojson_file("cascabel/paths/jrz2elp/bota.geojson")

waitline = WaitLine("cascabel/paths/jrz2elp/bota.geojson",
                    {"slow": 0.8, "fast": 0.2})
pdb.set_trace()
coordinates = waitline.get_path_coordinates()
# waitline.sampling_path['features'][0]['geometry']['coordinates']
