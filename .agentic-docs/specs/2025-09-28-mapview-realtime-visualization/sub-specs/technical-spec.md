# Technical Specification

This is the technical specification for the spec detailed in @.agentic-docs/specs/2025-09-28-mapview-realtime-visualization/spec.md

## Technical Requirements

- **Framework:** React with TypeScript
- **UI Library:** BlueprintJS for control panels and charts
- **Visualization:** HTML5 Canvas for map and car rendering (simple 2D visualization)
- **Real-time Updates:** WebSocket integration for simulation state updates
- **Data Visualization:** Basic line/bar charts using BlueprintJS components or Canvas
- **State Management:** React hooks for visualization parameters (zoom, refresh rate, filters)
- **Performance:** Efficient rendering for real-time updates (target 10-30 FPS)
- **Telemetry Processing:** CSV parsing and animation sequencing for historical data
- **Map Libraries:** Leaflet (react-leaflet) for interactive maps with GPS coordinates

## UI/UX Specifications

- **Layout:** Mapview page with map canvas, control sidebar, and charts panel
- **Map Visualization:** 2D top-down view of border crossing with roads, queues, service nodes
- **Car Display:** Colored circles/rectangles for cars, with trails and status indicators
- **Charts:** Live-updating charts for queue lengths, throughput, wait times
- **Controls:** Sliders, toggles, selects for viz parameters (zoom, speed, filters)
- **Telemetry Mode:** Toggle between live simulation and telemetry playback modes
- **Car Path Visualization:** Animated lines showing complete car journeys with timestamps
- **Historical Playback:** Timeline controls with play/pause/seek functionality and speed adjustment
- **Car List and Dashboard:** Scrollable list of cars with detailed metric dashboards

## Integration Requirements

- Connect to existing WebSocket at ws://localhost:8000/ws/{simulation_id}
- Parse simulation_update messages for car positions, queue states, statistics
- Maintain sync with simulation time and state
- Handle WebSocket reconnection and error states
- Load telemetry data from API endpoints or CSV files
- Convert simulation coordinates to GPS coordinates for map display
- Support GeoJSON boundary overlays for accurate geographic context

## Data Formats

### WebSocket Message Format (Updated)
```json
{
  "type": "simulation_update",
  "data": {
    "cars": [
      {
        "id": "car_1",
        "position": [longitude, latitude],
        "status": "arriving" | "queued" | "serving" | "completed",
        "velocity": number,
        "acceleration": number,
        "queue_id": number | null,
        "arrival_time": number,
        "service_start_time": number | null,
        "completion_time": number | null,
        "distance_traveled": number
      }
    ],
    "queues": [
      {
        "length": number,
        "throughput": number
      }
    ],
    "metrics": {
      "total_arrivals": number,
      "total_completions": number,
      "average_wait_time": number
    }
  }
}
```

### Telemetry CSV Format
```
timestamp,car_id,latitude,longitude,velocity,status,queue_id
2023-09-28T10:00:00Z,car_1,31.7619,-106.4850,15.5,arriving,null
2023-09-28T10:00:05Z,car_1,31.7620,-106.4848,12.3,queued,0
...
```

## API Requirements

- **GET /api/simulations/{id}/telemetry** - Retrieve telemetry data for completed simulation
- **POST /api/telemetry/upload** - Upload telemetry CSV for visualization
- **GET /api/simulations/{id}/status** - Get current simulation state for map initialization

## Dependencies

- react-leaflet for interactive maps
- leaflet for map tiles and controls
- papaparse for CSV parsing (telemetry data)
- Existing: BlueprintJS, WebSocket API