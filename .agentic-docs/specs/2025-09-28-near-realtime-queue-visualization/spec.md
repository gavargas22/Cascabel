# Spec Requirements Document

> Spec: Near-Realtime Queue Visualization
> Created: 2025-09-28

## Overview

Implement a near-realtime simulation with map-based visualization showing cars approaching and forming queues within a GeoJSON-defined border crossing area, incorporating physics-based movement, safe distances, acceleration, and dynamic service station selection based on queue lengths.

## User Stories

### Real-Time Traffic Visualization

As a researcher, I want to visualize cars approaching the border crossing and forming queues in near-realtime so that I can analyze traffic flow patterns and congestion.

Cars will appear on the map approaching the polygon area, slow down and form queues within the GeoJSON boundaries, with positions updating continuously.

### Realistic Car Movement

As a simulation user, I want cars to maintain safe distances and accelerate as the queue progresses, with movement influencing nearby cars, to simulate realistic human driving behavior.

Cars maintain approximately 2 meters safe distance, accelerate when the car ahead moves, and their movement affects following cars' decisions.

### Dynamic Queue Management

As a simulation enthusiast, I want to easily add multiple service stations and have cars choose the shortest queue when the path is clear, to model dynamic queue management.

Users can add service stations via UI, and cars will switch to shorter queues only if their path is unobstructed by surrounding traffic.

## Spec Scope

1. **Near-Realtime Simulation Engine** - Simulation runs continuously with adjustable time speed controls
2. **Mapbox Visualization** - Interactive map showing GeoJSON polygon, car positions, and service stations
3. **Physics-Based Car Movement** - Safe distances, acceleration based on queue progress, inter-car influence
4. **Dynamic Service Stations** - Easy addition of stations with shortest-queue selection logic
5. **Queue Confinement** - Cars form queues only within the GeoJSON polygon boundaries

## Out of Scope

- Historical data replay or import
- Multi-user real-time collaboration
- Advanced traffic light or signal controls
- Weather or environmental factors affecting movement

## Expected Deliverable

1. Interactive Mapbox map displaying cars moving and queuing within the GeoJSON area
2. Time control interface with buttons to accelerate or decelerate simulation speed
3. Dynamic station addition feature allowing users to add service stations and observe cars switching queues when paths are clear