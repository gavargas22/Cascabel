# API Specification

This is the API specification for the spec detailed in @.agentic-docs/specs/2026-01-10-rust-migration-high-performance/spec.md

## Endpoints

### REST API Endpoints

All REST endpoints maintain backward compatibility with existing FastAPI implementation.

---

### POST /simulate

**Purpose:** Start a new simulation with specified configuration

**Request Body:**
```json
{
  "border_config": {
    "num_queues": 3,
    "service_nodes_per_queue": 2,
    "arrival_rate": 0.2,
    "service_rate": 3.0,
    "safe_distance": 3.0
  },
  "simulation_config": {
    "max_simulation_time": 86400.0,
    "time_factor": 1.0,
    "enable_telemetry": true,
    "enable_position_tracking": true
  },
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa"
}
```

**Response:**
```json
{
  "simulation_id": "uuid-string",
  "status": "running",
  "websocket_url": "ws://localhost:8000/ws/{simulation_id}",
  "message": "Simulation started successfully"
}
```

**Errors:**
- `400 Bad Request`: Invalid configuration parameters
- `503 Service Unavailable`: Server at capacity

---

### GET /simulation/{simulation_id}/status

**Purpose:** Get current simulation status and metrics

**Parameters:**
- `simulation_id` (path): UUID of the simulation

**Response:**
```json
{
  "simulation_id": "uuid-string",
  "status": "running",
  "progress": 0.45,
  "current_time": 3600.0,
  "total_arrivals": 250,
  "total_completions": 180,
  "active_cars": 70,
  "message": null
}
```

**Errors:**
- `404 Not Found`: Simulation not found

---

### POST /simulation/{simulation_id}/stop

**Purpose:** Stop a running simulation and persist telemetry data

**Parameters:**
- `simulation_id` (path): UUID of the simulation

**Response:**
```json
{
  "simulation_id": "uuid-string",
  "status": "stopped",
  "message": "Simulation stopped. Saved 15000 telemetry records.",
  "telemetry_records_saved": 15000
}
```

**Errors:**
- `404 Not Found`: Simulation not found
- `500 Internal Server Error`: Failed to persist data

---

### GET /simulation/{simulation_id}/car/{car_id}

**Purpose:** Get detailed statistics for a specific car

**Parameters:**
- `simulation_id` (path): UUID of the simulation
- `car_id` (path): Integer car ID

**Response:**
```json
{
  "car_id": 42,
  "status": "queued",
  "queue_id": 1,
  "queue_position": 5,
  "position": [lon, lat],
  "velocity": 2.5,
  "acceleration": 0.0,
  "arrival_time": 1234567890.0,
  "queue_start_time": 1234567900.0,
  "wait_time": 120.5,
  "total_distance": 450.0,
  "path_progress": 0.75
}
```

**Errors:**
- `404 Not Found`: Simulation or car not found

---

### PUT /simulation/{simulation_id}/time_speed

**Purpose:** Update simulation time speed multiplier

**Request Body:**
```json
{
  "time_factor": 2.0
}
```

**Response:**
```json
{
  "status": "updated",
  "time_factor": 2.0
}
```

**Errors:**
- `404 Not Found`: Simulation not found
- `400 Bad Request`: Invalid time factor (must be > 0)

---

### POST /simulation/{simulation_id}/add_station

**Purpose:** Add a new service station to a queue

**Request Body:**
```json
{
  "queue_id": 0,
  "service_rate": 3.0,
  "service_time_variation": 0.2
}
```

**Response:**
```json
{
  "station_id": "q0_n3",
  "queue_id": 0,
  "service_rate": 3.0
}
```

**Errors:**
- `404 Not Found`: Simulation not found
- `400 Bad Request`: Invalid queue ID

---

### GET /crossing/{crossing_name}/config

**Purpose:** Get configuration data for a specific border crossing

**Parameters:**
- `crossing_name` (path): Name of crossing (e.g., "paso_del_norte")

**Response:**
```json
{
  "name": "paso_del_norte",
  "bounds": {
    "north": 31.77,
    "south": 31.75,
    "east": -106.44,
    "west": -106.50
  },
  "preferred_queue_geometry": [...],
  "slowdown_zones": [...]
}
```

**Errors:**
- `404 Not Found`: Crossing not found

---

## WebSocket Protocol

### Connection

**URL:** `ws://localhost:8000/ws/{simulation_id}`

**Headers:**
- `Origin`: Must be in allowed origins list
- `Sec-WebSocket-Protocol`: `cascabel.v1` (optional, for versioning)

### Message Format (Binary - MessagePack)

All messages are MessagePack-encoded binary frames.

#### Server -> Client: SimulationUpdate

Sent at 10Hz with full simulation state.

```rust
struct SimulationUpdate {
    msg_type: u8,           // 0x01
    timestamp: f64,         // Simulation time
    cars: Vec<CarState>,
    metrics: Metrics,
}

struct CarState {
    id: u32,
    position: [f32; 2],     // [lon, lat]
    velocity: f32,
    acceleration: f32,
    status: u8,             // 0=approaching, 1=queued, 2=serving, 3=completed
    queue_id: Option<u8>,
    queue_position: Option<u16>,
}

struct Metrics {
    total_arrivals: u32,
    total_completions: u32,
    average_wait_time: Option<f32>,
    active_cars: u32,
}
```

**Binary Layout (per car):**
| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | id (u32 LE) |
| 4 | 4 | lon (f32 LE) |
| 8 | 4 | lat (f32 LE) |
| 12 | 4 | velocity (f32 LE) |
| 16 | 4 | acceleration (f32 LE) |
| 20 | 1 | status (u8) |
| 21 | 1 | queue_id (u8, 0xFF = none) |
| 22 | 2 | queue_position (u16 LE, 0xFFFF = none) |
| **Total** | **24** | bytes per car |

For 5000 cars: ~120KB per update (vs ~500KB+ JSON)

#### Server -> Client: PositionOnlyUpdate

Sent at 30Hz for smooth animation interpolation (optional).

```rust
struct PositionOnlyUpdate {
    msg_type: u8,           // 0x02
    timestamp: f64,
    positions: Vec<(u32, f32, f32)>,  // [(id, lon, lat), ...]
}
```

**Binary Layout:**
| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | id (u32 LE) |
| 4 | 4 | lon (f32 LE) |
| 8 | 4 | lat (f32 LE) |
| **Total** | **12** | bytes per car |

For 5000 cars: ~60KB per update

#### Client -> Server: ControlMessage

```rust
enum ControlMessage {
    SetTimeSpeed { factor: f32 },
    AddCar { queue_id: Option<u8> },
    RemoveCar { car_id: u32 },
    Pause,
    Resume,
    RequestFullState,
}
```

#### Server -> Client: Error

```rust
struct ErrorMessage {
    msg_type: u8,           // 0xFF
    code: u16,
    message: String,
}
```

### Connection Lifecycle

1. **Connect**: Client opens WebSocket connection
2. **Handshake**: Server sends initial `SimulationUpdate` with full state
3. **Streaming**: Server sends updates at configured rate
4. **Heartbeat**: Server sends ping every 30s, client must respond with pong
5. **Disconnect**: Clean close with code 1000, or reconnect on error

### Reconnection Protocol

1. Client stores last received `timestamp`
2. On reconnect, client sends `RequestFullState`
3. Server sends full `SimulationUpdate`
4. Client interpolates between last known and new state

### Rate Limiting

- Maximum 100 control messages per second per client
- Exceeding limit results in `429 Too Many Requests` error message
- Persistent abuse results in connection termination

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| 1001 | 404 | Simulation not found |
| 1002 | 400 | Invalid configuration |
| 1003 | 400 | Invalid queue ID |
| 1004 | 400 | Simulation not running |
| 1005 | 503 | Server at capacity |
| 1006 | 500 | Internal server error |
| 1007 | 429 | Rate limit exceeded |

## CORS Configuration

```rust
// Allowed origins
const ALLOWED_ORIGINS: &[&str] = &[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
];

// CORS headers
Access-Control-Allow-Origin: {origin}
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

## Authentication (Future)

Currently no authentication required. Future implementation:

- Bearer token in `Authorization` header for REST
- Token query parameter `?token=xxx` for WebSocket
- JWT with 24-hour expiration
