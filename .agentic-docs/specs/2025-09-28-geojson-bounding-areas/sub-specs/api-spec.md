# API Specification

This is the API specification for the spec detailed in @.agentic-docs/specs/2025-09-28-geojson-bounding-areas/spec.md

## Endpoints

### GET /api/border-crossings

**Purpose:** Retrieve list of available border crossing GeoJSON files
**Parameters:** None
**Response:** 
```json
{
  "crossings": [
    {
      "id": "bota",
      "name": "Bridge of the Americas",
      "direction": "mx2usa"
    }
  ]
}
```
**Errors:** 500 if file system access fails

### POST /api/border-crossings/{crossing_id}/load

**Purpose:** Load and validate a specific border crossing GeoJSON file for simulation use
**Parameters:** crossing_id (path parameter)
**Response:** 
```json
{
  "status": "loaded",
  "polygon_bounds": {...},
  "start_point": [lng, lat],
  "stop_point": [lng, lat]
}
```
**Errors:** 404 if crossing not found, 400 if invalid GeoJSON

### GET /api/simulations/config

**Purpose:** Get current simulation configuration including loaded boundary
**Parameters:** None
**Response:** Includes boundary information if loaded
**Errors:** None