# Technical Specification

This is the technical specification for the spec detailed in @.agentic-docs/specs/2026-01-10-rust-migration-high-performance/spec.md

## Technical Requirements

### Backend Framework Selection: Axum

- **Framework**: Axum 0.7+ (Tokio-based async web framework)
- **Justification**:
  - Built on Tokio for high-performance async I/O
  - Native WebSocket support via `axum::extract::ws`
  - Type-safe extractors and middleware
  - Excellent performance in TechEmpower benchmarks
  - Strong ecosystem compatibility with Tower middleware
- **Alternatives Considered**:
  - Actix-web: Slightly faster but less ergonomic, actor model adds complexity
  - Warp: Good but less maintained than Axum
  - Rocket: Sync-first design, less suitable for WebSocket-heavy workloads

### WebSocket Implementation

- **Protocol**: Binary WebSocket frames with MessagePack serialization
- **Update Rate**: 10Hz (100ms intervals) for full state, 30Hz for position-only updates
- **Message Types**:
  - `SimulationState`: Full car states (position, velocity, acceleration, status)
  - `PositionUpdate`: Compact position-only updates (id, lat, lon)
  - `MetricsUpdate`: Queue statistics, throughput, wait times
- **Compression**: Optional LZ4 compression for large payloads (>10KB)
- **Connection Management**:
  - Heartbeat every 30 seconds
  - Automatic reconnection with exponential backoff
  - Session state preservation across reconnects

### Frontend Architecture Decision

**Recommendation: Keep React with WebGL Rendering Layer**

- **Justification**:
  - Rust WASM frontends (Leptos, Yew, Dioxus) are maturing but have smaller ecosystems
  - BlueprintJS UI components would need replacement
  - Map rendering libraries (Mapbox, MapLibre) have excellent React bindings
  - Team familiarity with React reduces migration risk
  - WebGL rendering can be integrated via deck.gl or custom layer

- **Alternative Option: Leptos with WASM**
  - Pro: Full Rust stack, shared types between frontend/backend
  - Con: Smaller ecosystem, fewer UI component libraries, steeper learning curve
  - Recommendation: Consider for v2 after backend migration proves successful

### WebGL Rendering Strategy

**Primary: deck.gl with ScatterplotLayer**

```javascript
// deck.gl approach - handles 100K+ points efficiently
import { Deck } from '@deck.gl/core';
import { ScatterplotLayer } from '@deck.gl/layers';

const layer = new ScatterplotLayer({
  id: 'cars',
  data: carsArray,          // Array of {position: [lon, lat], color, radius}
  getPosition: d => d.position,
  getRadius: 5,
  getFillColor: d => d.color,
  pickable: true,           // Enable click interactions
  updateTriggers: {
    getPosition: updateCounter  // Trigger re-render on position change
  }
});
```

**Advantages**:
- GPU instanced rendering (single draw call for all points)
- Built-in MapLibre/Mapbox integration
- Handles 100K+ points at 60 FPS
- Built-in picking for click interactions
- Automatic LOD (Level of Detail) culling

**Alternative: Custom WebGL Layer**

- For maximum control, implement custom MapLibre layer with instanced rendering
- More complex but allows custom shaders for car direction indicators
- Recommended only if deck.gl proves insufficient

### ECS Architecture for Simulation

**Framework: Bevy ECS (standalone, without full game engine)**

```rust
use bevy_ecs::prelude::*;

// Components
#[derive(Component)]
struct Position { x: f64, y: f64 }

#[derive(Component)]
struct Velocity { vx: f64, vy: f64 }

#[derive(Component)]
struct Acceleration { ax: f64, ay: f64 }

#[derive(Component)]
struct CarStatus(Status);

#[derive(Component)]
struct QueueMembership { queue_id: u32, position: u32 }

#[derive(Component)]
struct Path { waypoints: Vec<(f64, f64)>, current_index: usize }

// Systems
fn physics_system(mut query: Query<(&mut Position, &mut Velocity, &Acceleration)>, time: Res<Time>) {
    let dt = time.delta_seconds_f64();
    query.par_iter_mut().for_each(|(mut pos, mut vel, acc)| {
        vel.vx += acc.ax * dt;
        vel.vy += acc.ay * dt;
        pos.x += vel.vx * dt;
        pos.y += vel.vy * dt;
    });
}
```

**Benefits**:
- Automatic parallelization with `par_iter_mut()`
- Cache-friendly memory layout (SoA - Structure of Arrays)
- Compile-time query validation
- Easy to add new components without modifying existing code

**Alternative: Hecs**

- Lighter weight than Bevy ECS
- No automatic parallelization (use Rayon manually)
- Consider if Bevy ECS proves too heavy

### Spatial Indexing for Collision Detection

**Implementation: R-tree with rstar crate**

```rust
use rstar::{RTree, AABB, PointDistance};

#[derive(Clone, Copy)]
struct CarPoint {
    id: u32,
    position: [f64; 2],
}

impl rstar::RTreeObject for CarPoint {
    type Envelope = AABB<[f64; 2]>;
    fn envelope(&self) -> Self::Envelope {
        AABB::from_point(self.position)
    }
}

// Build tree (rebuild every N frames or use incremental updates)
let tree: RTree<CarPoint> = RTree::bulk_load(car_points);

// Query nearby cars
let nearby = tree.locate_within_distance(query_point, max_distance_squared);
```

**Performance Characteristics**:
- Build: O(n log n)
- Query: O(log n + k) where k = results
- Rebuild strategy: Full rebuild every 10 frames, or incremental for moving objects

**Alternative: Grid-based spatial hashing**

- Simpler implementation, O(1) query for uniform distributions
- Better for dense, uniform scenarios
- Consider if border crossing queues have predictable spatial patterns

### Binary Serialization Protocol

**Primary: MessagePack with rmp-serde**

```rust
use serde::{Serialize, Deserialize};
use rmp_serde::{Serializer, Deserializer};

#[derive(Serialize, Deserialize)]
struct CarUpdate {
    id: u32,
    position: [f32; 2],  // Use f32 for smaller payload
    velocity: f32,
    status: u8,          // Enum as u8
}

// Serialize
let bytes = rmp_serde::to_vec(&updates)?;

// ~50% smaller than JSON, ~10x faster to parse
```

**Message Format**:
| Field | Type | Bytes |
|-------|------|-------|
| id | u32 | 4 |
| lon | f32 | 4 |
| lat | f32 | 4 |
| velocity | f32 | 4 |
| status | u8 | 1 |
| **Total** | | **17** |

vs JSON: ~80-100 bytes per car

**Alternative: FlatBuffers**

- Zero-copy deserialization
- Schema evolution support
- More complex setup, consider if MessagePack bandwidth proves insufficient

### Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Cars simulated | 5,000+ | Count active entities |
| Physics tick rate | 100 Hz | Server-side timing |
| WebSocket update rate | 10 Hz | Message frequency |
| WebSocket latency | <100ms | Round-trip time |
| Frontend FPS | 60 | requestAnimationFrame timing |
| Memory (5K cars) | <500MB | Process memory |
| CPU (5K cars) | <50% single core | Profile with perf |

### Migration Strategy

**Phase 1: Backend Core (Weeks 1-2)**
1. Set up Rust project with Axum
2. Implement WebSocket endpoint
3. Port physics simulation to ECS
4. Implement spatial indexing

**Phase 2: API Parity (Weeks 3-4)**
1. Port all REST endpoints from FastAPI
2. Implement MessagePack serialization
3. Integration tests against existing frontend

**Phase 3: Frontend Optimization (Weeks 5-6)**
1. Replace Mapbox Markers with deck.gl layer
2. Implement binary WebSocket client
3. Performance testing and optimization

**Phase 4: Full Integration (Week 7)**
1. End-to-end testing
2. Performance benchmarking
3. Documentation and deployment

## External Dependencies

### Rust Backend Dependencies

- **axum** (0.7+) - Web framework with WebSocket support
  - **Justification**: Industry-standard async web framework, excellent performance, strong community

- **tokio** (1.0+) - Async runtime
  - **Justification**: Required by Axum, mature and battle-tested

- **bevy_ecs** (0.12+) - Entity Component System (standalone)
  - **Justification**: High-performance parallel ECS, perfect for simulation workloads

- **rstar** (0.11+) - R-tree spatial indexing
  - **Justification**: Efficient spatial queries for collision detection

- **rmp-serde** (1.1+) - MessagePack serialization
  - **Justification**: Fast binary serialization, ~50% smaller than JSON

- **serde** (1.0+) - Serialization framework
  - **Justification**: Industry-standard, required by rmp-serde

- **geo** (0.27+) - Geospatial primitives and algorithms
  - **Justification**: Rust equivalent of Shapely, needed for path calculations

- **proj** (0.27+) - Coordinate transformations
  - **Justification**: UTM to lat/lon conversions, equivalent to pyproj

- **geojson** (0.24+) - GeoJSON parsing
  - **Justification**: Load border crossing boundary definitions

### Frontend Dependencies (New)

- **deck.gl** (8.9+) - WebGL rendering framework
  - **Justification**: GPU-accelerated instanced rendering for 100K+ points

- **@deck.gl/mapbox** - MapLibre/Mapbox integration layer
  - **Justification**: Overlay deck.gl layers on existing map

- **msgpack-lite** or **@msgpack/msgpack** - MessagePack client
  - **Justification**: Decode binary WebSocket messages

### Development Dependencies

- **criterion** - Benchmarking framework
  - **Justification**: Performance regression testing

- **tracing** + **tracing-subscriber** - Structured logging
  - **Justification**: Production-grade observability

- **sqlx** (optional) - Async database driver
  - **Justification**: If PostgreSQL integration needed for telemetry storage
