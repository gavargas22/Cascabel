# API Usage Guide - Optimized System

## Quick Start

### Minimal Simulation Request

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "crossing_name": "paso_del_norte",
    "direction": "mx2usa",
    "border_config": {
      "num_queues": 3,
      "nodes_per_queue": [2, 2, 2],
      "arrival_rate": 20.0,
      "service_rates": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
    }
  }'
```

### Response

```json
{
  "simulation_id": "abc123...",
  "status": "running",
  "websocket_url": "ws://localhost:8000/ws/abc123...",
  "message": "Simulation started successfully"
}
```

## Traffic Directions

### Mexico → USA (Northbound)

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa"
}
```

- Cars spawn in **southern half** of bounding box (Mexico)
- Cars drive **north** to USA border
- Join queue at **south end** of queue line
- Travel **north** along queue to booth

### USA → Mexico (Southbound)

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "usa2mx"
}
```

- Cars spawn in **northern half** of bounding box (USA)
- Cars drive **south** to Mexico border
- Join queue at **north end** of queue line
- Travel **south** along queue to booth

## Available Crossings

### Paso del Norte

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa"
}
```

- **Location**: El Paso, TX / Ciudad Juárez, MX
- **Queue path**: Pre-defined geometry with 44 points
- **Slowdown zones**: 1 (booth)

### Bridge of the Americas

```json
{
  "crossing_name": "bridge_of_the_americas",
  "direction": "mx2usa"
}
```

- **Location**: El Paso, TX / Ciudad Juárez, MX
- **Slowdown zones**: 2 (license plate reader + booth)

## Full Request Example

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa",

  "border_config": {
    "num_queues": 3,
    "nodes_per_queue": [2, 2, 2],
    "arrival_rate": 20.0,
    "service_rates": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
    "queue_assignment": "shortest",
    "max_queue_length": 100,
    "safe_distance": 3.0
  },

  "simulation_config": {
    "max_simulation_time": 3600.0,
    "time_factor": 1.0,
    "enable_telemetry": true,
    "enable_position_tracking": true
  },

  "phone_config": {
    "sampling_rate": 10,
    "gps_accuracy_meters": 5.0,
    "accelerometer_noise_std": 0.1
  },

  "physics_config": {
    "min_speed_mps": 12.1,
    "max_speed_mps": 14.7,
    "safe_distance_meters": 3.0,
    "max_acceleration": 0.75,
    "max_deceleration": 1.25
  }
}
```

## Python Client Example

```python
import requests
import websockets
import asyncio
import json

# Start simulation
response = requests.post(
    "http://localhost:8000/simulate",
    json={
        "crossing_name": "paso_del_norte",
        "direction": "mx2usa",
        "border_config": {
            "num_queues": 3,
            "nodes_per_queue": [2, 2, 2],
            "arrival_rate": 20.0,
            "service_rates": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        }
    }
)

result = response.json()
simulation_id = result["simulation_id"]
ws_url = result["websocket_url"]

print(f"Simulation started: {simulation_id}")

# Connect to WebSocket for real-time updates
async def monitor_simulation():
    async with websockets.connect(ws_url) as websocket:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "simulation_update":
                cars = data["data"]["cars"]
                metrics = data["data"]["metrics"]

                print(f"Active cars: {len(cars)}")
                print(f"Total arrivals: {metrics['total_arrivals']}")
                print(f"Avg wait time: {metrics['average_wait_time']:.2f}s")

            elif data["type"] == "simulation_complete":
                print("Simulation complete!")
                break

# Run WebSocket monitor
asyncio.run(monitor_simulation())
```

## JavaScript/TypeScript Client

```typescript
interface SimulationRequest {
  crossing_name: string;
  direction: "mx2usa" | "usa2mx";
  border_config: {
    num_queues: number;
    nodes_per_queue: number[];
    arrival_rate: number;
    service_rates: number[];
  };
}

// Start simulation
async function startSimulation(request: SimulationRequest) {
  const response = await fetch("http://localhost:8000/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });

  const result = await response.json();
  return result;
}

// Connect to WebSocket
function monitorSimulation(simulationId: string) {
  const ws = new WebSocket(`ws://localhost:8000/ws/${simulationId}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "simulation_update") {
      const { cars, metrics } = data.data;

      // Update UI with car positions
      updateMap(cars);

      // Update metrics dashboard
      updateMetrics(metrics);
    }
  };

  ws.onerror = (error) => console.error("WebSocket error:", error);
  ws.onclose = () => console.log("Simulation ended");

  return ws;
}

// Usage
const request: SimulationRequest = {
  crossing_name: "paso_del_norte",
  direction: "mx2usa",
  border_config: {
    num_queues: 3,
    nodes_per_queue: [2, 2, 2],
    arrival_rate: 20.0,
    service_rates: [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
  }
};

const { simulation_id } = await startSimulation(request);
const ws = monitorSimulation(simulation_id);
```

## WebSocket Message Format

### Simulation Update

```json
{
  "type": "simulation_update",
  "data": {
    "cars": [
      {
        "id": "1",
        "position": [-106.4867, 31.7508],
        "status": "approaching",
        "velocity": 13.4,
        "acceleration": 0.0,
        "queue_id": 0,
        "arrival_time": 1234567890.0,
        "distance_traveled": 523.5
      }
    ],
    "queues": [
      {
        "length": 15,
        "throughput": 2
      }
    ],
    "metrics": {
      "total_arrivals": 42,
      "total_completions": 27,
      "average_wait_time": 180.5,
      "simulation_time": 600.0
    },
    "traffic_control_points": [
      {
        "type": "booth",
        "name": "Agent Inspection Booth",
        "position_meters": 1250.5,
        "coordinates": [-106.4867, 31.7500]
      }
    ],
    "service_nodes": [
      {
        "node_id": "q0_n0",
        "queue_id": 0,
        "is_busy": true,
        "current_car_id": "15",
        "service_rate": 3.0,
        "total_served": 8
      }
    ]
  }
}
```

### Simulation Complete

```json
{
  "simulation_id": "abc123...",
  "status": "completed",
  "progress": 1.0,
  "current_time": 3600.0,
  "total_arrivals": 150,
  "total_completions": 145,
  "message": "Simulation completed"
}
```

## Stop Simulation

```bash
curl -X POST http://localhost:8000/simulation/{simulation_id}/stop
```

Response:
```json
{
  "simulation_id": "abc123...",
  "status": "stopped",
  "message": "Simulation stopped. Saved 5000 telemetry records to database.",
  "telemetry_records_saved": 5000,
  "database_path": "/path/to/cascabel_telemetry.db"
}
```

## Get Simulation Status

```bash
curl http://localhost:8000/simulation/{simulation_id}/status
```

Response:
```json
{
  "simulation_id": "abc123...",
  "status": "running",
  "progress": 0.5,
  "current_time": 1800.0,
  "total_arrivals": 75,
  "total_completions": 60,
  "message": null
}
```

## Configuration Parameters

### Border Config

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `num_queues` | int | Number of parallel queues | 3 |
| `nodes_per_queue` | int[] | Service nodes per queue | [2,2,2] |
| `arrival_rate` | float | Cars/minute arrival rate | 20.0 |
| `service_rates` | float[] | Service rate per node (cars/min) | [3.0,...] |
| `queue_assignment` | str | "random", "shortest", "round_robin" | "shortest" |
| `max_queue_length` | int | Max cars per queue | 100 |
| `safe_distance` | float | Distance between cars (meters) | 3.0 |

### Simulation Config

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `max_simulation_time` | float | Max duration (seconds) | 86400.0 |
| `time_factor` | float | Simulation speed multiplier | 1.0 |
| `enable_telemetry` | bool | Generate telemetry data | true |
| `enable_position_tracking` | bool | Track car positions | true |

### Physics Config

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `min_speed_mps` | float | Min approach speed (m/s) | 12.1 |
| `max_speed_mps` | float | Max approach speed (m/s) | 14.7 |
| `safe_distance_meters` | float | Following distance | 3.0 |
| `max_acceleration` | float | Max accel (m/s²) | 0.75 |
| `max_deceleration` | float | Max brake (m/s²) | 1.25 |

## Common Scenarios

### High Traffic (Rush Hour)

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa",
  "border_config": {
    "num_queues": 6,
    "nodes_per_queue": [3, 3, 3, 3, 3, 3],
    "arrival_rate": 60.0,
    "service_rates": [3.5, 3.5, 3.5, ...]
  }
}
```

### Low Traffic (Night)

```json
{
  "crossing_name": "paso_del_norte",
  "direction": "mx2usa",
  "border_config": {
    "num_queues": 2,
    "nodes_per_queue": [1, 1],
    "arrival_rate": 5.0,
    "service_rates": [3.0, 3.0]
  }
}
```

### Fast Simulation (Testing)

```json
{
  "simulation_config": {
    "max_simulation_time": 600.0,
    "time_factor": 10.0
  }
}
```

## Performance Tips

1. **Reuse graph cache**: Multiple simulations of same crossing use cached graph
2. **Batch car creation**: System automatically batches cars for efficiency
3. **Adjust time_factor**: Use >1.0 for faster-than-real-time simulation
4. **Limit max_simulation_time**: Prevent runaway simulations
5. **Use WebSocket wisely**: Only one WebSocket connection per simulation

## Error Handling

### Invalid Crossing Name

```json
{
  "detail": "Crossing 'invalid_name' not found in bounding_boxes.json"
}
```

### Invalid Direction

```json
{
  "detail": "Invalid direction. Must be 'mx2usa' or 'usa2mx'"
}
```

### Graph Loading Failed

```json
{
  "detail": "Failed to load OSM graph for crossing. Check network connection."
}
```

## Next Steps

1. **Add your own crossings** to `bounding_boxes.json`
2. **Customize physics** with `physics_config`
3. **Integrate frontend** using WebSocket updates
4. **Analyze telemetry** from database after simulation
5. **Export data** via `/telemetry` endpoint
