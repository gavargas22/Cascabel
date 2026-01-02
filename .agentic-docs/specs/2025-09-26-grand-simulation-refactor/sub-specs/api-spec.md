# API Specification

This is the API specification for the spec detailed in @.agentic-docs/specs/2025-09-26-grand-simulation-refactor/spec.md

## Endpoints

### POST /grand-simulate

**Purpose:** Initiate a 24-hour grand simulation with configurable parameters.
**Parameters:** JSON body with simulation_config (duration=86400 default, rates, geojson_path, use_historical_data bool).
**Response:** {simulation_id: str, status: "running", websocket_url: str}
**Errors:** 400 if invalid config, 500 if simulation fails to start.

### GET /simulation/{id}/status

**Purpose:** Get current status and statistics of the simulation.
**Parameters:** None
**Response:** {status: str, progress: float, current_time: float, avg_wait_time: float, total_cars: int}
**Errors:** 404 if simulation not found.

### GET /simulation/{id}/visualization-data

**Purpose:** Fetch batched data for React visualization (e.g., car positions, queue states).
**Parameters:** ?timestamp=float (optional for specific time)
**Response:** JSON array of car states and map data.
**Errors:** 404 if no data available.

### WebSocket /ws/{id}

**Purpose:** Real-time streaming of simulation updates for live visualization.
**Parameters:** None
**Response:** Streamed JSON messages with updates (e.g., {type: "update", data: {...}}).
**Errors:** Closes connection on error with error message.