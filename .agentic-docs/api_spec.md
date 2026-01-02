# API Specification: Cascabel Simulation API

## Overview
The Cascabel API provides endpoints for running car queue simulations and retrieving telemetry data in CSV format, with realtime streaming capabilities.

## Base URL
```
http://localhost:8000
```

## Endpoints

### POST /simulate
Start a new simulation run.

**Request Body:**
```json
{
  "queue_config": {
    "path": "jrz2elp/bota",
    "arrival_rate": 0.5,  // cars per minute (lambda)
    "service_rate": 0.8,  // cars per minute (mu)
    "max_queue_length": 20
  },
  "phone_config": {
    "sampling_rate": 10,  // Hz
    "gps_noise": {
      "horizontal_accuracy": 5.0,  // meters
      "vertical_accuracy": 3.0     // meters
    },
    "accelerometer_noise": 0.01,  // m/s²
    "gyro_noise": 0.001           // rad/s
  },
  "simulation_config": {
    "duration": 3600,  // seconds
    "realtime": true   // enable realtime streaming
  }
}
```

**Response:**
```json
{
  "simulation_id": "sim_123456",
  "status": "running",
  "websocket_url": "ws://localhost:8000/ws/sim_123456",
  "estimated_completion": "2025-09-22T16:45:00Z"
}
```

### GET /simulation/{simulation_id}/status
Get the current status of a simulation.

**Response:**
```json
{
  "simulation_id": "sim_123456",
  "status": "running|completed|failed",
  "progress": 0.75,  // 0.0 to 1.0
  "cars_processed": 45,
  "current_queue_length": 8,
  "start_time": "2025-09-22T15:30:00Z",
  "estimated_completion": "2025-09-22T16:45:00Z"
}
```

### GET /simulation/{simulation_id}/telemetry
Retrieve telemetry data as CSV. For completed simulations, returns full dataset. For running simulations, returns data collected so far.

**Query Parameters:**
- `format`: "csv" (default) or "json"
- `start_time`: ISO timestamp to filter data from
- `end_time`: ISO timestamp to filter data to

**Response:** CSV data with headers matching the raw data format:
```
loggingTime,loggingSample,locationTimestamp_since1970,locationLatitude,locationLongitude,...
```

### WebSocket /ws/simulation/{simulation_id}
Realtime telemetry streaming during simulation.

**Message Format:**
```json
{
  "type": "telemetry",
  "data": {
    "loggingTime": "15:45.123",
    "loggingSample": 1234,
    "locationLatitude": 31.7660026,
    "locationLongitude": -106.4510884,
    "accelerometerAccelerationX": 0.204193115,
    "accelerometerAccelerationY": -0.76020813,
    "accelerometerAccelerationZ": -0.536392212,
    "activity": "automotive",
    "activityActivityConfidence": 2
  }
}
```

**Status Messages:**
```json
{
  "type": "status",
  "data": {
    "status": "running",
    "progress": 0.75,
    "cars_processed": 45,
    "current_queue_length": 8
  }
}
```

### GET /simulations
List all simulations.

**Query Parameters:**
- `status`: Filter by status ("running", "completed", "failed")
- `limit`: Maximum number of results (default 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "simulations": [
    {
      "simulation_id": "sim_123456",
      "status": "completed",
      "start_time": "2025-09-22T15:30:00Z",
      "end_time": "2025-09-22T16:45:00Z",
      "cars_processed": 67,
      "config": {...}
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### DELETE /simulation/{simulation_id}
Cancel a running simulation or delete completed simulation data.

**Response:**
```json
{
  "simulation_id": "sim_123456",
  "status": "cancelled"
}
```

## Error Responses
All endpoints return standard HTTP status codes. Error responses include:

```json
{
  "error": "InvalidRequest",
  "message": "Arrival rate must be positive",
  "details": {
    "field": "queue_config.arrival_rate",
    "value": -0.5
  }
}
```

## Authentication
Currently no authentication required for MVP. Add API key authentication in future versions.

## Rate Limiting
- 10 concurrent simulations per client
- 100 requests per minute per client
- WebSocket connections limited to 50 per simulation

## Data Formats

### Telemetry CSV Format
Matches the raw data format with the following key fields:
- **GPS**: locationLatitude, locationLongitude, locationAltitude, locationSpeed, locationCourse
- **Accuracy**: locationHorizontalAccuracy, locationVerticalAccuracy
- **Accelerometer**: accelerometerAccelerationX/Y/Z
- **Gyroscope**: gyroRotationX/Y/Z
- **Motion**: motionYaw, motionRoll, motionPitch, motionUserAccelerationX/Y/Z
- **Activity**: activity, activityActivityConfidence
- **Timestamps**: loggingTime, locationTimestamp_since1970, accelerometerTimestamp_sinceReboot

### Phone Configuration Parameters
- `sampling_rate`: Data collection frequency in Hz (1-100)
- `gps_noise`: GPS accuracy simulation parameters
- `accelerometer_noise`: Standard deviation for acceleration noise
- `gyro_noise`: Standard deviation for gyro noise
- `device_orientation`: Simulated phone orientation ("portrait", "landscape", "flat")

## Implementation Notes
- Use FastAPI for the web framework
- Implement background task processing for simulations
- Use Redis or in-memory storage for simulation state
- Stream CSV data efficiently for large datasets
- Handle WebSocket connection lifecycle properly

## Running the API

Start the server using `uv`:

```bash
uv run python scripts/run_api.py
```

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

## Future API Enhancements

### Multi-Crossing Support
```json
{
  "crossing_id": "san_ysidro",
  "geojson_path": "paths/us_mexico/san_ysidro.geojson",
  "lane_config": {
    "total_lanes": 24,
    "enabled_lanes": [1, 2, 3, 4, 5, 6],
    "lane_types": {
      "1-4": "standard",
      "5-6": "sentri"
    }
  }
}
```

### Lane Management Endpoints
- `GET /crossings` - List available border crossings
- `GET /crossing/{id}/lanes` - Get lane configuration for a crossing
- `POST /simulation/{id}/lane_switch` - Trigger lane switch for a car
- `WebSocket /ws/lane/{crossing_id}` - Lane-specific realtime updates

### Enhanced Telemetry Features
Future versions will include:
- Lane change event detection
- Gyroscope data validation
- Multi-lane position tracking
- Crossing-specific telemetry formats