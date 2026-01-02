# Implementation Plan: Car Queue Simulation MVP

## Phase 1: Core Model Enhancements (Week 1-2)

### 1.1 Enhanced Car Model
**Files to modify:**
- `cascabel/models/car.py`

**Requirements:**
- Add physics properties: mass, max_acceleration, max_velocity
- Implement realistic movement with acceleration limits
- Add position, velocity, acceleration tracking
- Integrate with telemetry generation

**Implementation:**
```python
class Car:
    def __init__(self, car_id, sampling_rate, phone_config, initial_position=0):
        self.car_id = car_id
        self.sampling_rate = sampling_rate
        self.phone_config = phone_config

        # Physics properties
        self.mass = 1500  # kg
        self.max_acceleration = 3.0  # m/s²
        self.max_velocity = 25.0  # m/s

        # State tracking
        self.position = initial_position
        self.velocity = 0.0
        self.acceleration = 0.0

        # Telemetry generators
        self.telemetry_gen = TelemetryGenerator(phone_config)
```

### 1.2 Multi-Car Queue Management
**Files to create/modify:**
- `cascabel/models/queue.py` (new)
- `cascabel/models/simulation.py`

**Requirements:**
- Implement CarQueue class with arrival/service processes
- Support multiple cars with safe following distances
- Queue length limits and balking behavior

### 1.3 Queuing Theory Integration
**Files to create:**
- `cascabel/models/queuing/arrival_process.py`
- `cascabel/models/queuing/service_process.py`
- `cascabel/models/queuing/mm1_queue.py`

**Requirements:**
- M/M/1 model implementation
- Exponential interarrival and service times
- Queue statistics tracking

## Phase 2: Telemetry Generation (Week 3-4)

### 2.1 Sensor Simulation Classes
**Files to create:**
- `cascabel/simulation/telemetry/gps_generator.py`
- `cascabel/simulation/telemetry/accelerometer_generator.py`
- `cascabel/simulation/telemetry/motion_generator.py`
- `cascabel/simulation/telemetry/telemetry_generator.py`

**Requirements:**
- Physics-based sensor data generation
- Realistic noise models
- Device orientation handling

### 2.2 CSV Data Generation
**Files to create:**
- `cascabel/simulation/csv_generator.py`

**Requirements:**
- Match raw data CSV format exactly
- Handle all sensor fields
- Efficient large dataset generation

## Phase 3: API Development (Week 5-6)

### 3.1 FastAPI Server Setup
**Files to create:**
- `api/main.py`
- `api/models.py`
- `api/routes/simulate.py`
- `api/routes/telemetry.py`
- `api/websocket.py`

**Requirements:**
- RESTful endpoints for simulation management
- Background task processing
- WebSocket streaming implementation

### 3.2 Simulation Orchestration
**Files to create:**
- `api/services/simulation_service.py`
- `api/services/telemetry_service.py`

**Requirements:**
- Async simulation execution
- Result caching and retrieval
- Realtime progress updates

## Phase 4: Integration and Testing (Week 7-8)

### 4.1 System Integration
**Requirements:**
- End-to-end simulation pipeline
- API to simulation data flow
- WebSocket streaming validation

### 4.2 Testing Suite
**Files to create:**
- `tests/test_car_physics.py`
- `tests/test_queue_theory.py`
- `tests/test_telemetry.py`
- `tests/test_api.py`

**Requirements:**
- Unit tests for all components
- Integration tests
- Performance benchmarks

### 4.3 Validation
**Requirements:**
- Statistical validation against queuing theory
- Telemetry data quality checks
- API performance testing

## Phase 5: Documentation and Deployment (Week 9-10)

### 5.1 Documentation
**Files to update/create:**
- `README.md`
- `docs/api.md`
- `docs/usage.md`

### 5.2 Deployment
**Files to create:**
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt` (update)
- `scripts/run_server.sh`

## Technical Architecture

### Development Environment
This project uses `uv` for Python package management and environment handling. All Python-related commands should use `uv`:

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run scripts
uv run python scripts/run_api.py

# Add new dependencies
uv add new_package
```

### Directory Structure
```
cascabel/
├── models/
│   ├── car.py (enhanced)
│   ├── waitline.py
│   ├── simulation.py (enhanced)
│   ├── queue.py (new)
│   └── queuing/ (new)
│       ├── arrival_process.py
│       ├── service_process.py
│       └── mm1_queue.py
├── simulation/
│   ├── telemetry/ (new)
│   │   ├── gps_generator.py
│   │   ├── accelerometer_generator.py
│   │   ├── motion_generator.py
│   │   └── telemetry_generator.py
│   └── csv_generator.py (new)
└── utils/
    └── io/
        └── geojson_file.py

api/ (new)
├── main.py
├── models.py
├── websocket.py
├── routes/
│   ├── simulate.py
│   └── telemetry.py
└── services/
    ├── simulation_service.py
    └── telemetry_service.py

tests/ (enhanced)
docs/
scripts/
```

### Dependencies to Add
```txt
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.0
python-multipart==0.0.6
aiofiles==23.2.1
```

### Key Classes Overview

#### Enhanced Car
- Physics simulation
- Telemetry generation integration
- Queue position tracking

#### CarQueue
- M/M/1 queue management
- Arrival/service process handling
- Statistics collection

#### TelemetryGenerator
- Coordinated sensor data generation
- Phone parameter handling
- CSV format compliance

#### SimulationService
- Async simulation execution
- Progress tracking
- Result management

## Risk Mitigation

### Technical Risks
1. **Performance**: Large simulations with many cars
   - Mitigation: Streaming results, background processing

2. **Accuracy**: Realistic physics and sensor simulation
   - Mitigation: Validation against real data, physics equations

3. **Concurrency**: Multiple simultaneous simulations
   - Mitigation: Async processing, resource limits

### Timeline Risks
1. **Complex Physics**: Car movement realism
   - Mitigation: Start with simplified models, iterate

2. **API Complexity**: WebSocket streaming
   - Mitigation: Prototype early, use established patterns

## Success Criteria

### Functional
- [ ] API accepts simulation parameters and returns CSV telemetry
- [ ] WebSocket streams realtime data during simulation
- [ ] Telemetry matches real data format and statistics
- [ ] Queue behavior follows M/M/1 theory

### Performance
- [ ] Handles 50+ cars per simulation
- [ ] <2 second API response times
- [ ] Realtime streaming <100ms latency

### Quality
- [ ] >90% test coverage
- [ ] Statistical validation passes
- [ ] Documentation complete

## Next Steps
1. Begin with Car model enhancement
2. Implement basic queue management
3. Develop telemetry generators
4. Build API skeleton
5. Integrate components iteratively

## Future Enhancements

### Border Crossing Generalization
- **Multi-Border Support**: Extend simulation to US-Mexico and US-Canada borders
- **GeoJSON Integration**: Use provided GeoJSON files to define crossing geometries and lane configurations
- **Dynamic Path Loading**: Load different border crossing layouts based on user selection
- **Crossing-Specific Parameters**: Different queue characteristics, processing times, and traffic patterns per crossing

### Advanced Lane Dynamics
- **Lane Switching Simulation**: Model cars changing lanes within the queue
- **Multi-Lane Support**: Support crossings with multiple parallel lanes
- **Lane-Specific Queues**: Separate queue management for each lane
- **Merging Behavior**: Simulate cars merging from multiple lanes into processing booths

### Enhanced Sensor Simulation
- **Gyroscope Data for Lane Changes**: Generate realistic gyroscope readings during lane switches
- **Turn Detection**: Simulate rotational motion when cars change direction
- **Orientation Tracking**: Maintain accurate device orientation throughout lane changes
- **Motion Correlation**: Ensure all sensors (GPS, accel, gyro) are correlated during maneuvers

### Geographic Expansion Features
```python
# Future crossing configuration
crossings = {
    "san_ysidro": {
        "geojson": "paths/us_mexico/san_ysidro.geojson",
        "lanes": 24,
        "typical_arrival_rate": 2.0,  # cars/minute
        "coordinates": [-117.026, 32.543]
    },
    "juarez": {
        "geojson": "paths/us_mexico/juarez.geojson",
        "lanes": 16,
        "typical_arrival_rate": 1.5,
        "coordinates": [-106.485, 31.761]
    }
}
```

### Lane Switching Implementation
```python
class LaneManager:
    def __init__(self, crossing_geojson):
        self.lanes = self.parse_lanes_from_geojson(crossing_geojson)
        self.lane_queues = {lane_id: MM1Queue() for lane_id in self.lanes}

    def switch_lane(self, car, from_lane, to_lane):
        """Handle lane switching with gyroscope simulation"""
        # Update car position
        # Generate rotational telemetry
        # Update queue positions
        pass
```