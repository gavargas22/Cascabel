//! Simulation module containing ECS-based physics engine
//!
//! This module contains:
//! - ECS components (Position, Velocity, Acceleration, etc.)
//! - Physics systems for movement simulation
//! - Queue management systems
//! - Resources for simulation configuration
//! - Spatial indexing for efficient collision detection
//! - High-level simulation engine API

pub mod components;
pub mod engine;
pub mod resources;
pub mod spatial;
pub mod systems;

pub use components::*;
pub use engine::*;
pub use resources::*;
pub use spatial::*;
pub use systems::*;
