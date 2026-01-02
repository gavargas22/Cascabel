# Spec Requirements Document

> Spec: GeoJSON Bounding Areas Integration
> Created: 2025-09-28

## Overview

Integrate GeoJSON polygons as bounding areas for border crossing simulations, using start and stop points to define traffic flow paths and ensure generated coordinates stay within defined geographical boundaries.

## User Stories

### Researcher Defines Border Crossing Bounds

As a researcher, I want to load GeoJSON files defining border crossing polygons and start/stop points, so that I can create realistic simulations bounded by actual geographical areas.

Users will select a border crossing (e.g., Bridge of the Americas), load its GeoJSON file, and the simulation will generate car movements only within the polygon boundaries, starting from the start point and aiming towards the stop point.

## Spec Scope

1. **GeoJSON Loading** - Load and parse GeoJSON files containing polygons and points for border crossings
2. **Bounding Validation** - Implement coordinate validation to ensure generated positions are within polygon bounds
3. **Traffic Flow Definition** - Use start and stop points to establish directional traffic flow within the crossing
4. **Path Generation** - Generate realistic vehicle paths that respect boundaries and flow direction

## Out of Scope

- Map visualization of polygons
- Multi-polygon border crossings
- Dynamic polygon editing or creation
- Integration with external mapping services

## Expected Deliverable

1. Simulations generate vehicle coordinates only within the defined GeoJSON polygon boundaries
2. Vehicles start at the specified start point and move towards the stop point
3. Coordinate generation rejects or corrects positions that fall outside polygon bounds
4. API endpoints support loading and using GeoJSON files for simulation configuration