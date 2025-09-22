# Cascabel

![alt text](https://github.com/gavargas22/Cascabel/raw/master/cascabel.jpg "Cascabel")

Simulates traffic on the border bridges with realistic car queue modeling and telemetry generation.

## Features

- **M/M/1 Queue Simulation**: Implements queuing theory for realistic car arrival and service patterns
- **Physics-Based Car Movement**: Enhanced car models with acceleration, velocity limits, and realistic physics
- **Realistic Telemetry Generation**: Generates GPS, accelerometer, and motion data matching real mobile device sensors
- **REST API**: FastAPI-based server for simulation management
- **Realtime Streaming**: WebSocket support for live telemetry data feed
- **Phone Parameters**: Configurable sampling rates, sensor noise, and device orientations

## Future Enhancements

### Geographic Expansion
- **Multi-Border Support**: US-Mexico and US-Canada border crossings
- **Dynamic GeoJSON Loading**: Support for custom border crossing geometries
- **Crossing-Specific Simulation**: Unique traffic patterns per border location

### Advanced Lane Dynamics
- **Lane Switching**: Realistic simulation of cars changing lanes
- **Multi-Lane Queues**: Support for crossings with multiple parallel lanes
- **Enhanced Gyroscope Data**: Rotational motion simulation during lane changes

## Quick Start

### Installation

This project uses `uv` for Python package management. Install dependencies using:

```bash
uv pip install -r requirements.txt
```

Or add individual packages:
```bash
uv add package_name
```

### Running the API

```bash
uv run python scripts/run_api.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Running Scripts

All Python scripts should be run using `uv`:

```bash
uv run python your_script.py
```

### Testing

```bash
uv run python -m unittest
```

### Basic Usage

```python
# Start a simulation
curl -X POST "http://localhost:8000/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_config": {
      "arrival_rate": 0.5,
      "service_rate": 0.8
    },
    "phone_config": {
      "sampling_rate": 10
    },
    "simulation_config": {
      "duration": 3600
    }
  }'
```

## API Endpoints

- `POST /simulate` - Start a new simulation
- `GET /simulation/{id}/status` - Get simulation status
- `GET /simulation/{id}/telemetry` - Download telemetry CSV
- `WebSocket /ws/{id}` - Realtime telemetry streaming

## Project Structure

```
cascabel/
├── models/                 # Core simulation models
│   ├── car.py             # Enhanced car with physics
│   ├── waitline.py        # Geographic path model
│   ├── queuing/           # Queue theory implementations
│   └── simulation.py      # Main simulation orchestrator
├── simulation/
│   ├── telemetry/         # Sensor data generators
│   └── csv_generator.py   # CSV output formatting
├── utils/
│   └── io/                # GeoJSON file handling
└── tests/                 # Unit tests

api/                       # FastAPI server
scripts/                   # Utility scripts
raw_data/                  # Real telemetry samples
```

## Testing

Test contained in `cascabel/tests/` can be run using the standard python library `unittest` by running the following command.

```bash
python -m unittest
```

## Development

The project includes comprehensive documentation in `.agentic-docs/` including:
- Project analysis and MVP requirements
- API specification
- Queuing theory implementation details
- Telemetry generation methodology