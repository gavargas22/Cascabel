# Spec Requirements Document

> Spec: Rust Migration for High-Performance Simulation
> Created: 2026-01-10

## Overview

Migrate Cascabel's backend and frontend to Rust to achieve high-performance real-time simulation capable of handling thousands of cars with low-latency WebSocket updates and efficient GPU-accelerated rendering.

## User Stories

### High-Volume Simulation Researcher

As a researcher studying large-scale border crossing traffic patterns, I want to simulate thousands of vehicles simultaneously, so that I can analyze realistic traffic scenarios without performance degradation.

The current Python/React implementation struggles with more than a few hundred cars due to:
- Python's GIL limiting concurrent physics calculations
- React DOM rendering overhead with individual Marker components
- Inefficient data serialization over WebSockets

With Rust, the simulation should handle 5,000+ cars at 60+ FPS with sub-100ms WebSocket latency.

### Real-Time Dashboard User

As a simulation operator, I want smooth, responsive visualization of all vehicles on the map, so that I can observe traffic patterns and queue dynamics in real-time without frame drops or UI lag.

The current Mapbox GL Marker-based approach creates one DOM element per car. With thousands of cars, this causes significant browser performance issues. A WebGL/Canvas-based instanced rendering approach would display all cars in a single draw call.

### Telemetry Data Analyst

As a data analyst, I want the simulation to generate accurate physics-based telemetry data at high frequency for many vehicles, so that I can use this synthetic data for machine learning and pattern recognition research.

The simulation must maintain physics accuracy (acceleration, velocity, position) while scaling to thousands of entities, which requires an efficient Entity Component System (ECS) architecture.

## Spec Scope

1. **Rust Backend with Axum** - High-performance async web framework with native WebSocket support for real-time simulation updates
2. **WebGL Frontend Rendering** - GPU-accelerated instanced rendering for thousands of moving points using deck.gl or custom WebGL
3. **ECS Simulation Engine** - Entity Component System architecture using Bevy ECS or Hecs for efficient parallel physics processing
4. **Spatial Indexing** - R-tree or grid-based spatial indexing for O(log n) collision detection and proximity queries
5. **Binary WebSocket Protocol** - MessagePack or FlatBuffers serialization for minimal latency data transfer

## Out of Scope

- Mobile native applications (iOS/Android)
- Full Bevy game engine integration (only use ECS components)
- Real-time multiplayer collaboration features
- Historical data replay from database (focus on live simulation)
- GPU-based physics simulation (CPU physics with GPU rendering)

## Expected Deliverable

1. Rust backend serving WebSocket connections with simulation state updates at 10Hz supporting 5,000+ concurrent cars with <100ms latency
2. Web frontend rendering 5,000+ moving car markers at 60 FPS using WebGL instanced rendering on a mid-range GPU
3. Simulation maintaining physics accuracy (position, velocity, acceleration) consistent with current Python implementation within 0.1% tolerance
