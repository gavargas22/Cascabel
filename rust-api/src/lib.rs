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

use axum::{http::Method, routing::{get, post, put, delete}, Router};
use tower_http::cors::{AllowOrigin, CorsLayer};
use tower_http::trace::TraceLayer;

pub use api::health::health_check;
pub use api::messages;
pub use api::websocket::{ws_handler, WebSocketState};
pub use api::simulation::{SimulationState, SimulationInstance};

/// Create the main application router with all routes and middleware
pub fn create_app() -> Router {
    create_app_with_state(WebSocketState::new(), SimulationState::new())
}

/// Create the main application router with custom state
pub fn create_app_with_state(ws_state: WebSocketState, sim_state: SimulationState) -> Router {
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
            axum::http::header::UPGRADE,
            axum::http::header::CONNECTION,
        ])
        .allow_credentials(true);

    // Create simulation routes with simulation state
    let simulation_routes = Router::new()
        .route("/simulate", post(api::simulation::start_simulation))
        .route("/simulation/:id/status", get(api::simulation::get_simulation_status))
        .route("/simulation/:id/state", get(api::simulation::get_simulation_state))
        .route("/simulation/:id/stop", post(api::simulation::stop_simulation))
        .route("/simulation/:id", delete(api::simulation::cancel_simulation))
        .route("/simulation/:id/time_speed", put(api::simulation::update_time_speed))
        .route("/simulation/:id/add_station", post(api::simulation::add_service_station))
        .route("/simulation/:id/service_node/:node_id", delete(api::simulation::remove_service_node))
        .route("/simulation/:id/add_car", post(api::simulation::add_car))
        .route("/simulation/:id/car/:car_id", get(api::simulation::get_car_details))
        .with_state(sim_state);

    // Create WebSocket routes with WebSocket state
    let ws_routes = Router::new()
        .route("/ws/:simulation_id", get(ws_handler))
        .with_state(ws_state);

    // Create crossing routes (no state needed)
    let crossing_routes = Router::new()
        .route("/border-crossings", get(api::crossings::get_border_crossings))
        .route("/crossing/:name/config", get(api::crossings::get_crossing_config))
        .route("/geojson/*path_name", get(api::crossings::get_geojson));

    // Build final router with all routes and middleware
    Router::new()
        // Health check (no state)
        .route("/health", get(health_check))
        // Merge in route groups
        .merge(ws_routes)
        .merge(simulation_routes)
        .merge(crossing_routes)
        .layer(cors)
        .layer(TraceLayer::new_for_http())
}
