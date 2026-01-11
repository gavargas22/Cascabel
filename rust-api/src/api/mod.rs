//! API module containing all HTTP handlers and routes
//!
//! This module contains:
//! - Health check endpoint
//! - WebSocket handler for real-time simulation streaming
//! - Message types for WebSocket communication

pub mod health;
pub mod messages;
pub mod websocket;
