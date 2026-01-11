//! Data models and types shared across the application
//!
//! This module contains:
//! - API request/response types
//! - WebSocket message types
//! - Configuration structures
//! - Simulation state types

pub mod config;
pub mod requests;

pub use config::*;
pub use requests::*;
