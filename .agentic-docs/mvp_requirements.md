# MVP Requirements: Car Queue Simulation API

## Core Functionality
The MVP must provide an API that simulates realistic car queues on border bridges and returns telemetry data in the same format as the raw CSV data, with realtime streaming capabilities.

## Functional Requirements

### 1. Enhanced Car Model
- **Physics Properties**: Mass, max acceleration, max velocity, current acceleration/velocity tracking
- **Movement Simulation**: Realistic acceleration/deceleration based on queue position
- **Sensor Simulation**: Generate GPS coordinates with noise, accelerometer data from physics

### 2. Multi-Car Queue Management
- **Queue Structure**: Support multiple cars with positions along the waitline
- **Safe Distances**: Maintain realistic following distances
- **Queue Dynamics**: Cars entering/leaving queue based on arrival/service rates

### 3. Queuing Theory Integration
- **M/M/1 Model**: Implement Poisson arrivals, exponential service times
- **Inter-arrival Times**: Generate realistic time gaps between cars
- **Service Rates**: Variable processing times at bridge crossings

### 4. Telemetry Generation
- **GPS Data**: Latitude, longitude, altitude with configurable noise
- **Accelerometer**: X, Y, Z acceleration derived from car physics
- **Motion Data**: Yaw, roll, pitch, rotation rates, attitude quaternions
- **Activity Recognition**: "automotive" activity with confidence levels
- **Device Parameters**: Sampling rate, sensor noise simulation

### 5. API Endpoints
- **POST /simulate**: Start simulation with parameters (queue length, arrival rate, phone settings)
- **GET /simulation/{id}/telemetry**: Retrieve CSV telemetry data
- **GET /simulation/{id}/status**: Get simulation status
- **WebSocket /ws/simulation/{id}**: Realtime telemetry streaming

### 6. Phone/Device Parameters
- **Sampling Rate**: Configurable data collection frequency
- **GPS Noise**: Accuracy simulation (horizontal/vertical accuracy)
- **Sensor Noise**: Accelerometer, gyro noise models
- **Device Orientation**: Simulate different phone orientations

### 7. Realtime Streaming
- **WebSocket Connection**: Live data feed during simulation
- **Data Format**: Same CSV structure streamed in realtime
- **Performance**: Handle multiple concurrent simulations

## Non-Functional Requirements

### Performance
- Support 10-50 cars per simulation
- Realtime streaming with <100ms latency
- Handle multiple simultaneous simulations

### Data Accuracy
- GPS positions accurate to within 5-10 meters
- Acceleration data consistent with car physics
- Realistic queue behavior matching real-world observations

### API Design
- RESTful endpoints with JSON responses
- Comprehensive error handling
- Input validation for simulation parameters

## Implementation Phases

### Phase 1: Core Simulation Engine
- Enhance Car model with physics
- Implement multi-car queue management
- Basic telemetry generation

### Phase 2: Queuing Theory
- M/M/1 model implementation
- Arrival/service rate configuration
- Statistical validation

### Phase 3: API Development
- FastAPI server setup
- CSV data generation endpoints
- Basic WebSocket streaming

### Phase 4: Advanced Features
- Phone parameter simulation
- Enhanced sensor noise models
- Performance optimization

### Phase 5: Testing & Validation
- Unit tests for all components
- Integration testing
- Performance benchmarking
- Data validation against real telemetry