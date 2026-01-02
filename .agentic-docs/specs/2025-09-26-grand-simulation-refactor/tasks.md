# Spec Tasks

## Tasks

- [ ] 1. Refactor API for Simplification and Grand Simulation Support
  - [ ] 1.1 Write tests for existing API endpoints
  - [ ] 1.2 Simplify and modularize existing endpoints using FastAPI best practices
  - [ ] 1.3 Add new /grand-simulate endpoint for 24-hour simulation initiation
  - [ ] 1.4 Add /simulation/{id}/visualization-data endpoint for batched data
  - [ ] 1.5 Enhance WebSocket /ws/{id} for efficient real-time streaming
  - [ ] 1.6 Update API documentation and error handling
  - [ ] 1.7 Verify all API tests pass

- [x] 2. Enhance Queuing Theory Integration
  - [x] 2.1 Write tests for queuing models (M/M/1 and M/M/c)
  - [x] 2.2 Implement time-varying arrival and service rates based on historical data
  - [x] 2.3 Integrate CBP RSS feed parsing for wait time data
  - [x] 2.4 Add randomized rate generation with scientific grounding
  - [x] 2.5 Implement variable wait times from car approach rates and inspection times
  - [x] 2.6 Validate queuing metrics against theoretical predictions
  - [x] 2.7 Verify all queuing tests pass

- [ ] 3. Implement 24-Hour Simulation Logic
  - [x] 3.1 Write tests for simulation duration and time stepping
  - [x] 3.2 Extend simulation class to support 24-hour runs (86400 seconds)
  - [x] 3.3 Implement time-of-day variations in traffic rates
  - [ ] 3.4 Add simulation statistics tracking for full-day metrics
  - [ ] 3.5 Optimize performance for long-duration runs
  - [ ] 3.6 Add simulation pause/resume capabilities
  - [x] 3.7 Verify all simulation tests pass

- [ ] 4. Develop React Visualization Integration
  - [x] 4.1 Write tests for visualization data fetching
  - [ ] 4.2 Update React components to handle batched API data
  - [ ] 4.3 Implement efficient map rendering with Leaflet clustering
  - [ ] 4.4 Add real-time updates via WebSocket integration
  - [ ] 4.5 Optimize rendering for 1000+ cars (virtualization/clustering)
  - [ ] 4.6 Add visualization controls for time scrubbing
  - [ ] 4.7 Verify all visualization tests pass

- [ ] 5. Integrate Historical Data and Finalize
  - [x] 5.1 Write tests for RSS feed integration
  - [x] 5.2 Implement feedparser for CBP wait time data
  - [x] 5.3 Add data caching and error handling for external feeds
  - [x] 5.4 Integrate historical data into simulation initialization
  - [x] 5.5 Update documentation with new features
  - [x] 5.6 Perform end-to-end testing of grand simulation
  - [x] 5.7 Verify all integration tests pass