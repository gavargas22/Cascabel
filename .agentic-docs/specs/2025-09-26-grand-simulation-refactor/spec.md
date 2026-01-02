# Spec Requirements Document

> Spec: Grand Simulation API Refactor
> Created: 2025-09-26

## Overview

Refactor and simplify the API to support a "grand simulation" that models a 24-hour period of border crossing traffic with variable wait times, integrating enhanced queuing theory for realistic car arrivals and inspections, while providing endpoints to drive an efficient React-based visualization with maps and real-time traffic rendering capable of handling large numbers of cars.

## User Stories

### Simulate Full-Day Border Traffic

As a researcher, I want to run a 24-hour simulation with realistic, variable traffic rates based on historical data, so that I can analyze wait time variations and queue behaviors over a full day.

The workflow involves initiating the simulation via API with parameters for duration and data sources, then monitoring progress and visualizing results in real-time on a map without performance issues.

### Visualize Large-Scale Traffic Efficiently

As a simulation enthusiast, I want a React-based tool that visualizes many simulated cars on a map in real-time, so that I can observe traffic patterns without high rendering demands.

The visualization fetches data from the API and renders efficiently, using techniques like clustering or simplified markers for scalability.

## Spec Scope

1. **API Refactoring** - Simplify existing endpoints and add new ones for grand simulation initiation, status checking, and real-time data streaming.
2. **Queuing Theory Enhancement** - Integrate and improve M/M/1 or M/M/c models with time-varying rates based on historical RSS data for realistic arrivals and inspections.
3. **24-Hour Simulation Logic** - Implement simulation runs over 24-hour periods with randomized yet data-informed traffic rates and variable wait times.
4. **React Visualization Integration** - Develop API support for efficient data delivery to a map-based React frontend that handles large car counts.
5. **Historical Data Integration** - Fetch and incorporate wait time data from CBP RSS feed to ground simulations in real-world patterns.

## Out of Scope

- Adding persistent database storage (use in-memory or file-based for now).
- Mobile app development.
- Real-time external integrations beyond the RSS feed.

## Expected Deliverable

1. A simplified API that can start a 24-hour grand simulation, provide real-time updates, and deliver data for visualization, testable via curl or Postman with successful simulation runs.
2. Enhanced queuing models that produce variable wait times matching theoretical metrics, verifiable through simulation statistics output.
3. A React visualization component that renders a map with many cars efficiently, testable in a browser without lag when simulating 1000+ cars.