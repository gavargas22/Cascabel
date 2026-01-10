//! Cascabel API - Main entry point
//!
//! High-performance Rust backend for border crossing simulation.
//! Provides REST API and WebSocket endpoints for real-time simulation control.

use cascabel_api::create_app;
use std::net::SocketAddr;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() {
    // Initialize tracing for structured logging
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "cascabel_api=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Create the application
    let app = create_app();

    // Define the address to listen on
    let addr = SocketAddr::from(([0, 0, 0, 0], 8001));

    tracing::info!("Cascabel API starting on {}", addr);
    tracing::info!("Health check available at http://{}/health", addr);

    // Start the server
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("Failed to bind to address");

    tracing::info!("Server listening on {}", addr);

    axum::serve(listener, app)
        .await
        .expect("Failed to start server");
}
