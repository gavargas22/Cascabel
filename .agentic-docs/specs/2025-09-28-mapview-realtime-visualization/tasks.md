# Spec Tasks

## Tasks

- [x] 1. Create Mapview Page Component
  - [x] 1.1 Write tests for mapview page component and navigation
  - [x] 1.2 Create MapviewPanel component with canvas layout and BlueprintJS structure
  - [x] 1.3 Add navigation button from Run tab to Mapview page
  - [x] 1.4 Set up WebSocket connection and data parsing for simulation updates
  - [x] 1.5 Test page navigation, layout rendering, and basic WebSocket connection
  - [x] 1.6 Verify all tests pass

- [x] 2. Implement Car Visualization
  - [x] 2.1 Write tests for car rendering, positioning, and real-time updates
  - [x] 2.2 Render cars as shapes on canvas with accurate positions
  - [x] 2.3 Add smooth car movement animations between updates
  - [x] 2.4 Implement color coding and status indicators for cars
  - [x] 2.5 Test car rendering, positioning, and real-time updates
  - [x] 2.6 Verify all tests pass

- [x] 3. Add Data Visualizations
  - [x] 3.1 Write tests for chart components and data updates
  - [x] 3.2 Create live-updating line chart for queue lengths over time
  - [x] 3.3 Add bar chart for current throughput and wait time metrics
  - [x] 3.4 Implement chart data updates from WebSocket messages
  - [x] 3.5 Test chart rendering, data accuracy, and real-time updates
  - [x] 3.6 Verify all tests pass

- [x] 4. Implement Visualization Controls
  - [x] 4.1 Write tests for control panel functionality and parameter changes
  - [x] 4.2 Add zoom level slider and pan controls for map canvas
  - [x] 4.3 Create controls for refresh rate and display filters (show trails, etc.)
  - [x] 4.4 Implement real-time application of visualization parameter changes
  - [x] 4.5 Test control interactions and immediate visual feedback
  - [x] 4.6 Verify all tests pass

- [x] 5. Integrate and Test Real-time Updates
  - [x] 5.1 Write tests for WebSocket data processing and state updates
  - [x] 5.2 Ensure efficient WebSocket data processing and state updates
  - [x] 5.3 Optimize canvas rendering for smooth 20+ FPS performance
  - [x] 5.4 Test complete workflow from simulation start to mapview visualization
  - [x] 5.5 Verify error handling, reconnection, and edge cases
  - [x] 5.6 Verify all tests pass

- [x] 6. Fix Real-time Map Display Issues
  - [x] 6.1 Debug WebSocket data format mismatch between API and frontend
  - [x] 6.2 Update API to send car position data in WebSocket messages
  - [x] 6.3 Fix frontend data parsing to handle correct message structure
  - [x] 6.4 Test real-time car position updates on map
  - [x] 6.5 Verify map shows cars moving in real-time during simulation

- [x] 7. Implement Telemetry Visualization Mode
  - [x] 7.1 Write tests for telemetry data loading and path rendering
  - [x] 7.2 Create telemetry data loader for CSV files
  - [x] 7.3 Implement car path animation from telemetry data
  - [x] 7.4 Add car selection and path highlighting functionality
  - [x] 7.5 Create playback controls for telemetry animation
  - [x] 7.6 Test telemetry visualization with sample data
  - [x] 7.7 Verify all tests pass

- [x] 8. Add Telemetry Data Management
  - [x] 8.1 Write tests for telemetry data storage and retrieval
  - [x] 8.2 Implement API endpoints for accessing simulation telemetry
  - [x] 8.3 Add telemetry data export functionality
  - [x] 8.4 Create data validation for telemetry CSV format
  - [x] 8.5 Test telemetry data loading from API and files
  - [x] 8.6 Verify all tests pass

- [x] 9. Implement Historical Playback
  - [x] 9.1 Write tests for playback controls and timeline functionality
  - [x] 9.2 Create playback control UI (play/pause/seek/speed)
  - [x] 9.3 Implement timeline scrubbing with visual feedback
  - [x] 9.4 Add speed adjustment controls for playback
  - [x] 9.5 Integrate playback with existing telemetry visualization
  - [x] 9.6 Test playback functionality with sample telemetry data
  - [x] 9.7 Verify all tests pass

- [x] 10. Implement Car List and Dashboard
  - [x] 10.1 Write tests for car list component and dashboard functionality
  - [x] 10.2 Create car list panel showing all cars in simulation
  - [x] 10.3 Implement car selection from list with highlighting on map
  - [x] 10.4 Create detailed car dashboard with real-time metrics
  - [x] 10.5 Add car filtering and sorting options in the list
  - [x] 10.6 Test car list updates and dashboard accuracy
  - [x] 10.7 Verify all tests pass

- [x] 11. Integrate Mapbox for Geographic Visualization
  - [x] 11.1 Install and configure react-map-gl components
  - [x] 11.2 Replace canvas rendering with Mapbox map component
  - [x] 11.3 Add proper geographic coordinate conversion (lat/lng to map coordinates)
  - [x] 11.4 Implement car markers on Mapbox map with real-time position updates
  - [x] 11.5 Add map styling and border crossing geometry overlay
  - [x] 11.6 Update zoom and pan controls to use Mapbox native controls
  - [x] 11.7 Test Mapbox integration with real geographic data
  - [x] 11.8 Update tests for Mapbox implementation and verify all tests pass

- [x] 12. Enhance Mapbox Telemetry Visualization
  - [x] Implement car path lines for telemetry data
  - [x] Add animated markers for telemetry playback
  - [x] Implement car path highlighting on selection
  - [x] Add performance optimization for large datasets