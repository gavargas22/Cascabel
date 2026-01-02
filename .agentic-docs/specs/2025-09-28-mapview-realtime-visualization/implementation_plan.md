# Implementation Plan

## Overview

This implementation plan outlines the steps to fix the realtime map display issues, add telemetry visualization capabilities, and integrate Mapbox for proper geographic visualization to the Cascabel simulation platform.

## Phase 1: Fix Real-time Map Display (Priority: High)

### 1.1 Debug WebSocket Data Flow
- Analyze current WebSocket message format in API vs. expected format in frontend
- Identify mismatch between simulation data structure and frontend expectations
- Document required data transformations

### 1.2 Update API WebSocket Messages
- Modify `run_simulation` function in `api/routers/simulations.py` to collect car data
- Add car position collection from all queues in BorderCrossing
- Update WebSocket message format to include car positions with GPS coordinates
- Test WebSocket message sending with mock data

### 1.3 Update Frontend Data Parsing
- Fix MapviewPanel component to handle correct message structure
- Update car rendering logic to use real position data
- Test real-time updates with updated API

### 1.4 Coordinate System Integration
- Implement conversion from simulation coordinates to GPS coordinates
- Integrate with existing GeoJSON boundary data
- Test coordinate accuracy against known border crossing locations

## Phase 2: Telemetry Visualization (Priority: Medium)

### 2.1 Telemetry Data Loading
- Create API endpoint to retrieve telemetry data from completed simulations
- Implement CSV parsing functionality for uploaded telemetry files
- Add data validation for telemetry format consistency

### 2.2 Path Animation System
- Design car path data structure for animation sequences
- Implement time-based animation playback
- Add interpolation between telemetry points for smooth movement

### 2.3 Car Selection and Highlighting
- Add car identification system with unique colors/IDs
- Implement click-to-select functionality for individual cars
- Create path highlighting with opacity/transparency effects

### 2.4 Playback Controls
- Add play/pause/seek controls for telemetry animation
- Implement speed adjustment for playback
- Add timeline scrubbing functionality
- Integrate with historical simulation data

## Phase 3: Car Monitoring and Dashboard (Priority: Medium)

### 3.1 Car List Implementation
- Implement scrollable car list component
- Create detailed car dashboard with real-time metrics
- Add car selection and highlighting functionality
- Integrate with existing WebSocket data updates

### 3.2 Dashboard Metrics
- Display comprehensive vehicle state information
- Show real-time position, speed, wait time, and queue status
- Implement car filtering and sorting options

## Phase 4: Mapbox Geographic Integration (Priority: High)

### 4.1 Mapbox Setup and Configuration
- Install and configure react-map-gl components
- Set up Mapbox API key management
- Initialize Mapbox map component with proper viewport settings

### 4.2 Replace Canvas with Mapbox Rendering
- Replace HTML5 canvas rendering with Mapbox map component
- Implement proper geographic coordinate conversion (lat/lng to map coordinates)
- Add map styling and border crossing geometry overlay using GeoJSON layers

### 4.3 Real-time Car Visualization on Mapbox
- Implement car markers on Mapbox map with real-time position updates
- Add car marker styling with status indicators and color coding
- Update zoom and pan controls to use Mapbox native controls

### 4.4 Mapbox Telemetry Visualization
- Implement car path lines using Mapbox GeoJSON layers for telemetry data
- Add animated car markers for telemetry playback with smooth transitions
- Create car path highlighting on selection with visual effects

### 4.5 Performance Optimization
- Optimize rendering performance for large telemetry datasets
- Add map bounds and viewport management for telemetry data
- Implement data throttling for high-frequency updates

## Testing Strategy

### Unit Tests
- WebSocket message parsing
- Coordinate conversion functions
- Telemetry data validation
- Animation timing calculations
- Mapbox component rendering

### Integration Tests
- End-to-end WebSocket data flow
- Telemetry file upload and parsing
- Map rendering with real simulation data
- Mapbox geographic visualization accuracy

### Performance Tests
- Rendering performance with 100+ cars on Mapbox
- WebSocket message throughput
- Memory usage during long simulations
- Mapbox viewport performance with large datasets

## Risk Assessment

### High Risk
- Coordinate system accuracy - incorrect GPS conversion could make maps unusable
- WebSocket data format changes - could break existing functionality
- Mapbox API key management and service reliability

### Medium Risk
- Performance with large telemetry datasets on Mapbox
- Browser compatibility for Mapbox GL JS
- Coordinate conversion accuracy across different border regions

### Low Risk
- UI control additions
- CSV parsing edge cases
- Car dashboard metric calculations

## Success Criteria

1. Real-time map displays cars moving during active simulations using Mapbox
2. Telemetry visualization shows accurate car paths from CSV data on geographic map
3. Map loads within 3 seconds of simulation start with proper geographic context
4. Smooth animation at 15+ FPS during playback on Mapbox
5. Car selection works reliably with 50+ cars on screen with highlighting
6. Car list updates in real-time and shows accurate metrics
7. Car dashboard displays comprehensive vehicle state information
8. Mapbox integration provides accurate geographic visualization of border crossings
9. Telemetry playback works smoothly with path visualization on map
10. Performance remains stable with large datasets and real-time updates