# Path Utilities

This directory contains utilities for working with OpenStreetMap data for the Cascabel border crossing simulation.

## Modules

### graph_retrieval.py

Utilities for downloading and caching road network graphs from OpenStreetMap.

**Key Functions:**
- `load_bounding_boxes()` - Load bounding boxes from bounding_boxes.json
- `retrieve_graph(area_name, bbox, ...)` - Retrieve a road network graph
- `retrieve_and_cache_graph(area_name, bbox, ...)` - Retrieve or load from cache
- `retrieve_all_graphs(...)` - Retrieve graphs for all defined areas

**CLI Usage:**
```bash
# Retrieve all graphs (uses cache if available)
uv run python cascabel/paths/utils/graph_retrieval.py

# Force re-download for all areas
uv run python cascabel/paths/utils/graph_retrieval.py --force

# Retrieve specific area only
uv run python cascabel/paths/utils/graph_retrieval.py --area paso_del_norte

# Use different network type
uv run python cascabel/paths/utils/graph_retrieval.py --network-type walk
```

**Python Usage:**
```python
from cascabel.paths.utils.graph_retrieval import retrieve_and_cache_graph, load_bounding_boxes

# Load bounding boxes
bboxes = load_bounding_boxes()

# Get graph (from cache or download)
graph = retrieve_and_cache_graph('paso_del_norte', bboxes['paso_del_norte'])
```

### feature_retrieval.py

Utilities for downloading and caching geographic features (roads, buildings, etc.) from OpenStreetMap.

**Key Functions:**
- `load_bounding_boxes()` - Load bounding boxes from bounding_boxes.json
- `retrieve_features(area_name, bbox, tags)` - Retrieve features
- `retrieve_and_cache_features(area_name, bbox, tags, ...)` - Retrieve or load from cache
- `retrieve_all_features(tags, ...)` - Retrieve features for all defined areas

**CLI Usage:**
```bash
# Retrieve all features with default highway tags
uv run python cascabel/paths/utils/feature_retrieval.py

# Retrieve with custom tags
uv run python cascabel/paths/utils/feature_retrieval.py --tags '{"amenity": true, "building": true}'

# Retrieve specific area only
uv run python cascabel/paths/utils/feature_retrieval.py --area paso_del_norte

# Force re-download
uv run python cascabel/paths/utils/feature_retrieval.py --force
```

**Python Usage:**
```python
from cascabel.paths.utils.feature_retrieval import retrieve_and_cache_features, load_bounding_boxes

# Load bounding boxes
bboxes = load_bounding_boxes()

# Get features (from cache or download)
tags = {'highway': ['residential', 'primary', 'secondary', 'trunk']}
features = retrieve_and_cache_features('paso_del_norte', bboxes['paso_del_norte'], tags)
```

### path_finding.py

Core path finding utilities for calculating optimal routes between points.

**Key Functions:**
- `load_graph(area_name)` - Load cached graph for an area
- `get_optimal_path(start, end, ...)` - Get optimal path as GeoJSON LineString
- `get_optimal_path_feature(start, end, ...)` - Get optimal path as GeoJSON Feature

**NEW: Detailed Road Geometry**

By default, paths now include all the curves and details from the actual roads (not just straight lines between intersections). This provides 2-3x more vertices for realistic simulation.

**Python Usage:**
```python
from cascabel.paths.utils.path_finding import get_optimal_path, load_graph

# Example coordinates (longitude, latitude)
start = (-106.482, 31.743)
end = (-106.487, 31.750)

# Option 1: Let it load the graph automatically (with detailed geometry)
linestring = get_optimal_path(start, end)
# Returns: ~37 vertices following actual road curves

# Option 2: Simple mode (straight lines between nodes only)
linestring_simple = get_optimal_path(start, end, interpolate=False)
# Returns: ~14 vertices with straight connections

# Option 3: Pre-load graph for multiple queries (more efficient)
graph = load_graph('paso_del_norte')
linestring1 = get_optimal_path(start, end, graph=graph)
linestring2 = get_optimal_path(start, another_end, graph=graph)

# Get as GeoJSON Feature with properties
from cascabel.paths.utils.path_finding import get_optimal_path_feature

feature = get_optimal_path_feature(
    start,
    end,
    properties={"name": "Route 1", "type": "optimal"},
    interpolate=True  # Default: use detailed geometry
)
```

**Interpolation Comparison:**
```python
# Compare the difference
path_simple = get_optimal_path(start, end, interpolate=False)
path_detailed = get_optimal_path(start, end, interpolate=True)

print(f"Simple: {len(path_simple['coordinates'])} vertices")
print(f"Detailed: {len(path_detailed['coordinates'])} vertices")
# Output: Simple: 14 vertices
#         Detailed: 37 vertices (2.6x more detail)
```

## Data Files

### bounding_boxes.json

Defines geographic bounding boxes for areas of interest. Format:
```json
{
  "area_name": [west, south, east, north]
}
```

Example:
```json
{
  "paso_del_norte": [-106.52833, 31.71882, -106.44473, 31.78589]
}
```

### Cached Files

The scripts automatically cache downloaded data in the `cascabel/paths/` directory:

- `{area_name}_graph.graphml` - Road network graphs
- `{area_name}_features.pkl` - Geographic features

These caches are reused unless `--force` flag is used.

## Examples

### Example 1: Download and Cache All Data

```bash
# Download road networks for all areas
uv run python cascabel/paths/utils/graph_retrieval.py

# Download features for all areas
uv run python cascabel/paths/utils/feature_retrieval.py
```

### Example 2: Find Optimal Path

```python
from cascabel.paths.utils.path_finding import get_optimal_path

# Define start and end points (longitude, latitude)
border_crossing = (-106.487, 31.750)
highway_entrance = (-106.482, 31.743)

# Get optimal driving path
path = get_optimal_path(highway_entrance, border_crossing)

print(f"Path has {len(path['coordinates'])} waypoints")
# Output: Path has 14 waypoints
```

### Example 3: Working with Multiple Areas

```python
from cascabel.paths.utils.graph_retrieval import load_bounding_boxes, retrieve_all_graphs

# Load all defined areas
bboxes = load_bounding_boxes()
print(f"Available areas: {list(bboxes.keys())}")

# Download/cache graphs for all areas
graphs = retrieve_all_graphs()

# Use individual graphs
for area_name, graph in graphs.items():
    print(f"{area_name}: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
```

### Example 4: Custom Network Types

```python
from cascabel.paths.utils.graph_retrieval import retrieve_and_cache_graph, load_bounding_boxes

bboxes = load_bounding_boxes()

# Get walking network instead of driving
walking_graph = retrieve_and_cache_graph(
    'paso_del_norte',
    bboxes['paso_del_norte'],
    network_type='walk'
)
```

## Adding New Areas

1. Add bounding box to `bounding_boxes.json`:
```json
{
  "paso_del_norte": [-106.52833, 31.71882, -106.44473, 31.78589],
  "new_area": [west, south, east, north]
}
```

2. Download data for the new area:
```bash
uv run python cascabel/paths/utils/graph_retrieval.py --area new_area
uv run python cascabel/paths/utils/feature_retrieval.py --area new_area
```

3. Use the new area in path finding:
```python
path = get_optimal_path(start, end, area_name='new_area')
```
