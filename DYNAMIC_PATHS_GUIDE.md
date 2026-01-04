# Dynamic Path Generation System

## Overview

The Cascabel simulation now supports **dynamic path generation** using optimal routing from OpenStreetMap road networks. Instead of using fixed GeoJSON paths, the system can now:

1. **Generate unique paths for each car** from random starting points within bounding boxes
2. **Support country-specific origins** (Mexico or USA)
3. **Use real road networks** via OpenStreetMap and optimal routing algorithms
4. **Integrate slowdown zones** automatically from bounding_boxes.json

## Key Components

### 1. Bounding Boxes Configuration

Location: `cascabel/paths/bounding_boxes.json`

This file defines border crossings with:
- **bounding_box**: Geographic area `[west, south, east, north]`
- **slowdown_zones**: Traffic control points (booths, license plate readers, etc.)

Example:
```json
{
  "paso_del_norte": {
    "bounding_box": [-106.52833, 31.71882, -106.44473, 31.78589],
    "slowdown_zones": [
      {
        "type": "Feature",
        "properties": {
          "type": "booth",
          "name": "Agent Inspection Booth"
        },
        "geometry": {
          "coordinates": [-106.48674974382509, 31.750000662385048],
          "type": "Point"
        }
      }
    ]
  }
}
```

### 2. Dynamic Path Generator

Location: `cascabel/paths/utils/dynamic_path_generator.py`

Functions:
- `generate_dynamic_path()` - Create optimal path from random start to booth
- `get_country_origin_zones()` - Split bounding box by country
- `get_booth_location()` - Extract booth coordinates
- `get_slowdown_zones_on_path()` - Calculate zone positions along path

### 3. DynamicWaitLine Class

Location: `cascabel/models/dynamic_waitline.py`

Replaces the old static WaitLine with dynamically generated paths:

```python
from cascabel.models.dynamic_waitline import DynamicWaitLine

# Create a dynamic path from Mexico to the border
waitline = DynamicWaitLine(
    crossing_name="paso_del_norte",
    country="mexico",  # or "usa"
    graph=None,  # Will auto-load
    starting_point=None,  # Random point in Mexico zone
    line_length_seed=1.0
)
```

### 4. Updated Car Model

Cars now have their own individual paths:

```python
car = Car(
    car_id=1,
    waitline=dynamic_waitline,  # Each car can have unique path
    ...
)
```

## How to Use

### Option 1: Via API (Recommended)

Start a simulation with dynamic paths:

```python
import requests

simulation_request = {
    "border_config": {
        "num_queues": 3,
        "nodes_per_queue": [2, 2, 2],
        "arrival_rate": 20.0,
        "service_rates": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
    },
    "use_dynamic_paths": True,  # Enable dynamic path generation
    "crossing_name": "paso_del_norte",  # Border crossing name
    "country_of_origin": "mexico"  # Cars coming from Mexico
}

response = requests.post(
    "http://localhost:8000/simulate",
    json=simulation_request
)
```

### Option 2: Programmatically

```python
from cascabel.models.dynamic_waitline import DynamicWaitLine
from cascabel.models.border_crossing import BorderCrossing
from cascabel.models.simulation import Simulation
from cascabel.paths.utils.path_finding import load_graph

# Load road network graph
graph = load_graph("paso_del_norte")

# Create a reference waitline (each car gets its own)
waitline = DynamicWaitLine(
    crossing_name="paso_del_norte",
    country="mexico",
    graph=graph
)

# Create border crossing with dynamic paths enabled
border_crossing = BorderCrossing(
    waitline=waitline,
    config=border_config,
    crossing_name="paso_del_norte",
    graph=graph,
    use_dynamic_paths=True
)

# When cars are added, they get unique paths
border_crossing.default_country = "mexico"
car, queue_idx = border_crossing.add_car(country="mexico")
# car.waitline contains a unique path for this car
```

## Country-Specific Origins

The system automatically splits the bounding box into country zones:

- **Mexico zone**: Southern portion of bounding box
- **USA zone**: Northern portion of bounding box

Cars are randomly placed within their country's zone and routed to the booth.

## Slowdown Zones Integration

Slowdown zones from `bounding_boxes.json` are automatically:

1. Projected onto each car's unique path
2. Converted to position-along-path (meters)
3. Used by physics engine to slow cars down

Zone types:
- **booth**: Complete stop zone at border crossing booth
- **slowdown**: Reduced speed zone (e.g., license plate readers)

## Testing

Run the test suite:

```bash
cd cascabel/paths/utils
python test_dynamic_paths.py
```

This will:
- Test path generation for both Mexico and USA
- Verify slowdown zones are loaded correctly
- Generate sample paths saved as GeoJSON
- Validate multiple cars get different random starting points

## Migration from Old System

### Old System (Static GeoJSON)
```python
waitline = WaitLine(
    "cascabel/paths/usa2mx/bota.geojson",
    {"slow": 0.8, "fast": 0.2},
    line_length_seed=1.0
)
```

### New System (Dynamic Paths)
```python
waitline = DynamicWaitLine(
    crossing_name="paso_del_norte",
    country="mexico",
    starting_point=None  # Random
)
```

Both systems are compatible - the API automatically uses DynamicWaitLine when `use_dynamic_paths=True`.

## Benefits

1. **Realistic traffic patterns** - Cars start from distributed locations
2. **Flexible origins** - Support both Mexico→USA and USA→Mexico traffic
3. **Accurate routing** - Uses real road networks from OpenStreetMap
4. **Scalable** - Each car can have a unique path
5. **Automatic slowdown zones** - No manual GeoJSON editing required

## File Structure

```
cascabel/
├── paths/
│   ├── bounding_boxes.json           # Crossing definitions
│   └── utils/
│       ├── dynamic_path_generator.py # Path generation logic
│       ├── path_finding.py           # Optimal routing
│       ├── graph_retrieval.py        # OSM graph loading
│       └── test_dynamic_paths.py     # Test suite
├── models/
│   ├── dynamic_waitline.py           # Dynamic path class
│   ├── car.py                        # Updated with waitline per car
│   ├── queue.py                      # Updated for car-specific paths
│   ├── border_crossing.py            # Dynamic path support
│   └── simulation.py                 # Updated position tracking
└── api/
    └── routers/
        └── simulations.py            # API with dynamic path support
```

## Next Steps

1. **Add more crossings** to `bounding_boxes.json`
2. **Tune country zones** for more accurate geographic splits
3. **Implement traffic direction changes** (e.g., rush hour reversals)
4. **Add path caching** for improved performance
5. **Visualize paths** in the frontend dashboard
