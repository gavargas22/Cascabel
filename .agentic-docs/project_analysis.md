# Project Analysis: Cascabel Traffic Simulation

## Overview
Cascabel is a Python-based simulation project for modeling traffic queues on border bridges. The project aims to simulate realistic car movement in queues, generating telemetry data that mimics real-world sensor data from mobile devices.

## Current Architecture

### Core Models
- **Car**: Basic car model with sampling rate, position tracking, and simple movement mechanics
- **WaitLine**: Represents the queue path using GeoJSON data, handles geographic projections (UTM), and defines speed regimes (slow/fast)
- **Simulation**: Orchestrates the simulation loop, advances time, and manages car movement
- **Crossing**: Additional model for bridge crossings (not fully analyzed yet)

### Key Components
- **GeoJSON Paths**: Geographic paths for different bridge routes (jrz2elp, elp2jrz)
- **Raw Data**: Real sensor data from mobile devices in CSV format containing GPS, accelerometer, gyro, and motion data
- **Utils**: GeoJSON file handling utilities

### Current Limitations
1. **Single Car Simulation**: Only supports one car at a time
2. **Basic Physics**: Car model lacks realistic physics (mass, acceleration limits, velocity constraints)
3. **No Queuing Theory**: No implementation of arrival/service rates or queue management
4. **No Telemetry Generation**: No realistic sensor data generation
5. **No API**: No web API for accessing simulation results
6. **No Realtime Streaming**: No WebSocket support for live data

## Dependencies
- numpy, pandas: Data processing
- shapely, geopandas, pyproj, utm: Geographic/geospatial operations
- geojson: GeoJSON handling
- fastapi, uvicorn, websockets: Web API and realtime streaming
- pydantic: Data validation
- aiofiles: Async file operations

## Development Environment
This project uses `uv` for Python package management and environment handling. All Python-related actions (installing dependencies, running scripts, etc.) should be performed using `uv` commands.

### Package Management with uv
```bash
# Add dependencies
uv add package_name

# Install from requirements.txt
uv pip install -r requirements.txt

# Run Python scripts
uv run python script.py

# Run the API server
uv run python scripts/run_api.py
```

## Data Format
The raw CSV data includes comprehensive sensor readings:
- GPS: latitude, longitude, altitude, speed, course, accuracy
- Accelerometer: x, y, z acceleration
- Gyroscope: rotation rates
- Motion: yaw, roll, pitch, user acceleration, attitude quaternions
- Activity recognition: automotive detection
- Device orientation and other metadata

## MVP Requirements Analysis
To achieve the MVP goal of generating realistic car queue telemetry via API:

### Essential Enhancements
1. **Enhanced Car Physics**: Add mass, acceleration/velocity limits, realistic movement equations
2. **Multi-Car Support**: Implement queue management with multiple cars maintaining safe distances
3. **Queuing Theory Integration**: M/M/1 model for arrival/service rates, inter-arrival time distributions
4. **Realistic Telemetry Generation**: Generate GPS positions with noise, accelerometer data from physics
5. **Phone Parameters**: Incorporate sampling rates, sensor noise models
6. **API Development**: FastAPI server with endpoints for simulation runs
7. **Realtime Streaming**: WebSocket implementation for live telemetry feed

### Technical Challenges
- Realistic physics simulation for car movement in queues
- Accurate sensor noise modeling
- Geographic coordinate transformations
- Efficient multi-car simulation
- Realtime data streaming performance

## Future Enhancements

### Geographic Expansion
The simulation will be generalized to support any border crossing along US-Mexico and US-Canada borders. Key features include:

- **Dynamic GeoJSON Loading**: Accept provided GeoJSON files defining crossing geometries, lane layouts, and coordinate boundaries
- **Multi-Crossing Support**: Configure different crossings with unique characteristics:
  - Lane counts and configurations
  - Typical traffic patterns and arrival rates
  - Geographic coordinates and boundaries
  - Processing booth layouts

### Advanced Lane Dynamics
- **Lane Switching**: Simulate cars changing lanes within queue areas
- **Multi-Lane Queues**: Support crossings with multiple parallel lanes
- **Merging Behavior**: Model cars merging from lanes into processing areas
- **Lane-Specific Parameters**: Different queue characteristics per lane

### Enhanced Gyroscope Simulation
- **Lane Change Detection**: Generate realistic gyroscope data during lane switches
- **Rotational Motion**: Simulate yaw, pitch, and roll during maneuvers
- **Orientation Tracking**: Maintain accurate device orientation throughout movement
- **Sensor Correlation**: Ensure gyroscope data correlates with GPS and accelerometer readings

### Example Crossing Configurations
```python
# Future crossing definitions
us_mexico_crossings = {
    "san_ysidro": {"lanes": 24, "coordinates": [-117.026, 32.543]},
    "otay_mesa": {"lanes": 12, "coordinates": [-116.936, 32.545]},
    "tecate": {"lanes": 2, "coordinates": [-116.626, 32.577]},
    "juarez": {"lanes": 16, "coordinates": [-106.485, 31.761]},
    "nuevo_laredo": {"lanes": 8, "coordinates": [-99.507, 27.476]}
}

us_canada_crossings = {
    "peace_arch": {"lanes": 6, "coordinates": [-122.386, 49.002]},
    "lynden_alaska": {"lanes": 1, "coordinates": [-122.456, 48.947]},
    "blaine": {"lanes": 10, "coordinates": [-122.747, 48.993]}
}
```

## Technical Challenges
- Realistic physics simulation for car movement in queues
- Accurate sensor noise modeling
- Geographic coordinate transformations
- Efficient multi-car simulation
- **Future**: Multi-lane coordination and lane switching logic
- **Future**: Gyroscope data generation for rotational movements
- **Future**: Dynamic GeoJSON parsing for different border crossings