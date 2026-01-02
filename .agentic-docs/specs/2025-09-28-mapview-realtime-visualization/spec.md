# Spec Requirements Document

> Spec: mapview-realtime-visualization
> Created: 2025-09-28
> Updated: 2025-09-28

## Overview

Implement a mapview page accessible after starting a simulation, displaying real-time simulation progression with car movements, data visualizations of current simulation state, and controls to adjust visualization parameters in real-time. Additionally, provide functionality to visualize completed simulations using telemetry data, showing individual car paths and movements.

## User Stories

### Real-time Map Visualization

As a user, after starting a simulation, I want to view a map showing the real-time positions and movements of cars approaching and crossing the border, so that I can observe the simulation dynamics visually.

**Detailed Workflow:** User starts simulation in Run tab, clicks "View Map" button, navigates to mapview page showing border crossing area with cars moving in real-time, color-coded by status (approaching, queued, serving, completed).

### Live Data Visualizations

As a researcher, I want to see live data visualizations of queue lengths, throughput, and other metrics during the simulation, so that I can monitor performance indicators in real-time.

**Detailed Workflow:** On mapview page, user sees charts updating live: queue length over time, cars processed per minute, average wait times, with data refreshing every few seconds via WebSocket.

### Adjustable Visualization Parameters

As a simulation enthusiast, I want to adjust visualization parameters like zoom level, data refresh rate, and display options in real-time without stopping the simulation, so that I can customize my viewing experience.

**Detailed Workflow:** User uses control panel on mapview to adjust map zoom, toggle car trails, change chart time windows, modify refresh intervals, with changes applying immediately to the live visualization.

### After-the-Fact Telemetry Visualization

As a researcher, I want to visualize completed simulations using collected telemetry data, showing the complete paths taken by individual cars throughout the simulation, so that I can analyze traffic patterns and car behaviors post-simulation.

**Detailed Workflow:** User selects a completed simulation or loads telemetry CSV data, views map with animated car paths showing historical movements, can select individual cars to highlight their specific paths, and see timestamps for different phases of the journey.

### Historical Playback Controls

As a researcher, I want to replay completed simulations with adjustable playback speed and timeline scrubbing, so that I can review specific moments or time periods in detail.

**Detailed Workflow:** User loads completed simulation data, uses playback controls to play/pause the animation, scrub through the timeline to jump to specific times, adjust playback speed (0.5x to 4x), and see synchronized data visualizations updating alongside the map animation.

### Car List and Dashboard

As a researcher, I want to see a list of all cars currently in the simulation and be able to select individual cars to view detailed dashboards of their current state, so that I can monitor specific vehicle metrics and behaviors.

**Detailed Workflow:** User sees a scrollable list of all cars in the simulation on the mapview page, clicks on a car to select it, and views a detailed dashboard showing real-time metrics like position, velocity, acceleration, queue status, arrival time, and service progress.

## Spec Scope

1. **Mapview Page** - New page/tab with map canvas showing border crossing area
2. **Car Visualization** - Real-time display of car positions, movements, and status indicators
3. **Data Visualizations** - Live charts for queue lengths, throughput, wait times
4. **Visualization Controls** - Adjustable parameters for zoom, refresh rate, display filters
5. **Telemetry Playback** - Load and visualize completed simulation telemetry data with car path animations
6. **Car Path Identification** - Ability to select and highlight individual car paths in telemetry visualization
7. **Historical Playback** - Ability to replay completed simulations with adjustable speed and timeline scrubbing
8. **Car List and Dashboard** - List of all simulation cars with detailed dashboards showing individual car metrics

## Out of Scope

- Changing simulation parameters (arrival rates, service rates, etc.)
- Advanced 3D or 3D-like visualizations
- Multi-simulation comparison views
- Exporting or saving visualizations
- Real-time collaboration features

## Expected Deliverable

1. A mapview interface with real-time car positions and movements on a border crossing map
2. Live-updating charts showing simulation metrics (queue lengths, throughput, etc.)
3. Adjustable visualization controls for zoom, refresh rate, and display options
4. Seamless integration with running simulations via WebSocket updates
5. Telemetry visualization mode for completed simulations showing animated car paths
6. Car selection and path highlighting functionality in telemetry mode
7. Historical playback controls for replaying completed simulations with adjustable speed and timeline scrubbing
8. Car list panel showing all simulation cars with detailed dashboards for individual car metrics