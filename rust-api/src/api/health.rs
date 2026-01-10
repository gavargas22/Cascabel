//! Health check endpoint for service monitoring
//!
//! Provides a simple endpoint that returns the service status,
//! version, and service name for monitoring and orchestration tools.

use axum::Json;
use serde::{Deserialize, Serialize};

/// Response structure for the health check endpoint
#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    /// Current service status
    pub status: String,
    /// Service version from Cargo.toml
    pub version: String,
    /// Service identifier
    pub service: String,
}

/// Health check endpoint handler
///
/// Returns JSON response with service health information.
///
/// # Example Response
/// ```json
/// {
///     "status": "healthy",
///     "version": "0.1.0",
///     "service": "cascabel-api"
/// }
/// ```
pub async fn health_check() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        service: "cascabel-api".to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check_returns_healthy() {
        let response = health_check().await;
        assert_eq!(response.status, "healthy");
        assert_eq!(response.service, "cascabel-api");
    }
}
