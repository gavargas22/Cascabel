# Spec Tasks

> Spec: Rust Migration for High-Performance Simulation
> Created: 2026-01-10

## Tasks

- [x] 1. Initialize Rust Backend Project Structure
  - [x] 1.1 Write integration tests for basic Axum server startup and health check endpoint
  - [x] 1.2 Create Rust project with Cargo.toml including all dependencies (axum, tokio, bevy_ecs, rstar, rmp-serde, serde, geo, proj, geojson)
  - [x] 1.3 Set up project directory structure (src/main.rs, src/lib.rs, src/api/, src/simulation/, src/models/)
  - [x] 1.4 Implement basic Axum server with health check endpoint and CORS configuration
  - [x] 1.5 Configure Docker build for Rust backend alongside existing Python backend
  - [x] 1.6 Verify all tests pass and server starts correctly

- [x] 2. Implement ECS Simulation Engine with Bevy ECS
  - [x] 2.1 Write unit tests for ECS components (Position, Velocity, Acceleration, CarStatus, QueueMembership, Path)
  - [x] 2.2 Define all ECS component structs matching current Python simulation data model
  - [x] 2.3 Write tests for physics system (position/velocity/acceleration integration)
  - [x] 2.4 Implement physics_system with parallel iteration using par_iter_mut()
  - [x] 2.5 Write tests for car spawning and despawning systems
  - [x] 2.6 Implement car arrival and completion systems
  - [x] 2.7 Write tests for queue assignment and lane switching behavior
  - [x] 2.8 Implement queue management systems with lane switching logic
  - [x] 2.9 Verify physics accuracy within 0.1% tolerance of Python implementation

- [ ] 3. Implement R-tree Spatial Indexing
  - [ ] 3.1 Write tests for R-tree insertion and nearest neighbor queries
  - [ ] 3.2 Implement CarPoint struct with RTreeObject trait
  - [ ] 3.3 Write tests for collision detection queries within distance threshold
  - [ ] 3.4 Implement spatial query system for finding nearby cars
  - [ ] 3.5 Write benchmarks for R-tree performance with 5000+ entities
  - [ ] 3.6 Implement R-tree rebuild strategy (full rebuild every 10 frames)
  - [ ] 3.7 Verify O(log n) query performance characteristics

- [ ] 4. Implement WebSocket Server with Binary Protocol
  - [ ] 4.1 Write tests for WebSocket connection lifecycle (connect, stream, disconnect)
  - [ ] 4.2 Implement WebSocket endpoint at /ws/{simulation_id}
  - [ ] 4.3 Write tests for MessagePack serialization of SimulationUpdate messages
  - [ ] 4.4 Implement CarState and Metrics structs with serde serialization
  - [ ] 4.5 Write tests for PositionOnlyUpdate compact message format
  - [ ] 4.6 Implement 10Hz full state updates and optional 30Hz position-only updates
  - [ ] 4.7 Write tests for client control messages (pause, resume, time speed)
  - [ ] 4.8 Implement ControlMessage handling and heartbeat mechanism
  - [ ] 4.9 Verify <100ms WebSocket latency with 5000+ cars

- [ ] 5. Port REST API Endpoints from FastAPI
  - [ ] 5.1 Write integration tests for POST /simulate endpoint
  - [ ] 5.2 Implement /simulate endpoint with BorderConfig and SimulationConfig parsing
  - [ ] 5.3 Write tests for GET /simulation/{id}/status endpoint
  - [ ] 5.4 Implement simulation status endpoint with progress and metrics
  - [ ] 5.5 Write tests for POST /simulation/{id}/stop endpoint
  - [ ] 5.6 Implement stop endpoint with telemetry persistence
  - [ ] 5.7 Write tests for GET /simulation/{id}/car/{car_id} endpoint
  - [ ] 5.8 Implement car detail endpoint with full statistics
  - [ ] 5.9 Write tests for PUT /simulation/{id}/time_speed and POST /simulation/{id}/add_station
  - [ ] 5.10 Implement time speed control and station addition endpoints
  - [ ] 5.11 Write tests for GET /crossing/{name}/config endpoint
  - [ ] 5.12 Implement crossing config endpoint with GeoJSON loading
  - [ ] 5.13 Verify API parity with existing FastAPI implementation

- [ ] 6. Add deck.gl WebGL Rendering Layer to Frontend
  - [ ] 6.1 Write tests for deck.gl ScatterplotLayer rendering with mock car data
  - [ ] 6.2 Add deck.gl dependencies to package.json (@deck.gl/core, @deck.gl/layers, @deck.gl/mapbox)
  - [ ] 6.3 Create DeckGLOverlay component integrating with existing Mapbox map
  - [ ] 6.4 Write tests for car position updates triggering layer re-render
  - [ ] 6.5 Implement ScatterplotLayer with getPosition, getRadius, getFillColor based on car status
  - [ ] 6.6 Write tests for pickable interactions (car click/hover)
  - [ ] 6.7 Implement car picking and selection highlighting
  - [ ] 6.8 Write performance tests verifying 60 FPS with 5000+ points
  - [ ] 6.9 Verify rendering performance on mid-range GPU

- [ ] 7. Implement Binary WebSocket Client in Frontend
  - [ ] 7.1 Write tests for MessagePack message decoding
  - [ ] 7.2 Add @msgpack/msgpack dependency to package.json
  - [ ] 7.3 Create WebSocketClient class handling binary frames
  - [ ] 7.4 Write tests for SimulationUpdate message parsing
  - [ ] 7.5 Implement typed message parsing for all message types (SimulationUpdate, PositionOnlyUpdate, Error)
  - [ ] 7.6 Write tests for reconnection with exponential backoff
  - [ ] 7.7 Implement automatic reconnection and RequestFullState on reconnect
  - [ ] 7.8 Write tests for control message sending (pause, resume, time speed)
  - [ ] 7.9 Implement ControlMessage serialization and sending
  - [ ] 7.10 Verify client handles 10Hz updates without dropped frames

- [ ] 8. Integration Testing and Performance Benchmarking
  - [ ] 8.1 Write end-to-end tests for simulation start, WebSocket stream, and stop
  - [ ] 8.2 Create benchmark suite measuring cars simulated, physics tick rate, WebSocket latency
  - [ ] 8.3 Write load tests verifying 5000+ concurrent cars
  - [ ] 8.4 Measure and document frontend FPS with 5000+ cars
  - [ ] 8.5 Measure and document memory usage (<500MB target)
  - [ ] 8.6 Measure and document CPU usage (<50% single core target)
  - [ ] 8.7 Compare physics accuracy between Rust and Python implementations
  - [ ] 8.8 Verify all performance targets from technical spec are met

- [ ] 9. Documentation and Deployment Configuration
  - [ ] 9.1 Write API documentation for new Rust endpoints
  - [ ] 9.2 Update Docker Compose configuration to use Rust backend
  - [ ] 9.3 Create migration guide for switching from Python to Rust backend
  - [ ] 9.4 Document WebSocket binary protocol format
  - [ ] 9.5 Update frontend README with deck.gl configuration
  - [ ] 9.6 Create performance tuning guide
  - [ ] 9.7 Verify all documentation is accurate and complete
