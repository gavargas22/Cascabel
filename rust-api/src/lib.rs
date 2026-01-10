//! Cascabel API - High-performance Rust backend for border crossing simulation
//!
//! This crate provides:
//! - REST API endpoints for simulation control
//! - WebSocket streaming for real-time updates
//! - ECS-based physics simulation engine
//! - Spatial indexing for efficient collision detection

pub mod api;
pub mod models;
pub mod simulation;

use axum::{http::Method, routing::get, Router};
use tower_http::cors::{AllowOrigin, CorsLayer};
use tower_http::trace::TraceLayer;

pub use api::health::health_check;

/// Create the main application router with all routes and middleware
pub fn create_app() -> Router {
    // Configure CORS
    // Note: Cannot use wildcard (*) headers/methods with credentials
    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::list([
            "http://localhost:3000".parse().unwrap(),
            "http://127.0.0.1:3000".parse().unwrap(),
        ]))
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([
            axum::http::header::CONTENT_TYPE,
            axum::http::header::AUTHORIZATION,
        ])
        .allow_credentials(true);

    // Build router with routes and middleware
    Router::new()
        .route("/health", get(health_check))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
}
