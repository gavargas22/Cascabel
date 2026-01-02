# Spec Tasks

## Tasks

- [x] 1. Update Backend Simulation Engine for Near-Realtime Physics
  - [x] 1.1 Write tests for car physics model with safe distance constraints
  - [x] 1.2 Implement 2-meter safe distance logic in car movement
  - [x] 1.3 Add acceleration mechanics based on queue progress
  - [x] 1.4 Implement inter-car influence on movement decisions
  - [x] 1.5 Modify simulation loop for configurable time multipliers
  - [x] 1.6 Verify all physics tests pass

- [x] 2. Implement Mapbox Visualization Component
  - [x] 2.1 Write tests for Mapbox map rendering with GeoJSON layers
  - [x] 2.2 Create React component with Mapbox GL JS integration
  - [x] 2.3 Add GeoJSON polygon layer for border crossing area
  - [x] 2.4 Implement animated car markers on map
  - [x] 2.5 Add service station markers with queue indicators
  - [x] 2.6 Verify map visualization tests pass

- [x] 3. Establish WebSocket Real-Time Communication
  - [x] 3.1 Write tests for WebSocket connection and message handling
  - [x] 3.2 Set up Socket.io server endpoint for simulation updates
  - [x] 3.3 Implement frontend WebSocket client for receiving updates
  - [x] 3.4 Add car position broadcasting from backend
  - [x] 3.5 Handle connection errors and reconnection logic
  - [x] 3.6 Verify WebSocket communication tests pass

- [x] 4. Develop Dynamic Service Station Management
  - [x] 4.1 Write tests for station addition and queue assignment logic
  - [x] 4.2 Implement API endpoint for adding service stations
  - [x] 4.3 Add shortest-queue selection algorithm with path clearance checks
  - [x] 4.4 Create UI controls for adding stations on map
  - [x] 4.5 Integrate station switching into car movement logic
  - [x] 4.6 Verify station management tests pass

- [x] 5. Add Time Control Interface and Queue Confinement
  - [x] 5.1 Write tests for time speed controls and polygon constraints
  - [x] 5.2 Implement UI buttons for simulation speed adjustment
  - [x] 5.3 Add API endpoint for changing simulation speed
  - [x] 5.4 Enforce queue formation within GeoJSON polygon boundaries
  - [x] 5.5 Add car position validation against polygon geometry
  - [x] 5.6 Verify time controls and confinement tests pass