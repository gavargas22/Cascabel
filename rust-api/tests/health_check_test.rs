//! Integration tests for health check endpoint and server startup
//!
//! These tests verify:
//! 1. The Axum server starts correctly
//! 2. The health check endpoint returns 200 OK
//! 3. The health check response contains expected fields
//! 4. CORS headers are properly configured

use axum_test::TestServer;
use cascabel_api::create_app;
use serde_json::Value;

/// Test that the server can be created without errors
#[tokio::test]
async fn test_server_creates_successfully() {
    let app = create_app();
    let _server = TestServer::new(app).expect("Failed to create test server");
}

/// Test that the health check endpoint returns 200 OK
#[tokio::test]
async fn test_health_check_returns_ok() {
    let app = create_app();
    let server = TestServer::new(app).expect("Failed to create test server");

    let response = server.get("/health").await;

    response.assert_status_ok();
}

/// Test that the health check response contains expected JSON fields
#[tokio::test]
async fn test_health_check_response_format() {
    let app = create_app();
    let server = TestServer::new(app).expect("Failed to create test server");

    let response = server.get("/health").await;

    response.assert_status_ok();

    let json: Value = response.json();

    // Verify required fields exist
    assert!(json.get("status").is_some(), "Response should have 'status' field");
    assert!(json.get("version").is_some(), "Response should have 'version' field");
    assert!(json.get("service").is_some(), "Response should have 'service' field");

    // Verify status is "healthy"
    assert_eq!(
        json["status"].as_str(),
        Some("healthy"),
        "Status should be 'healthy'"
    );

    // Verify service name
    assert_eq!(
        json["service"].as_str(),
        Some("cascabel-api"),
        "Service should be 'cascabel-api'"
    );
}

/// Test that CORS headers are present for allowed origins
#[tokio::test]
async fn test_cors_headers_present() {
    let app = create_app();
    let server = TestServer::new(app).expect("Failed to create test server");

    // Make a request with an Origin header
    let response = server
        .get("/health")
        .add_header("Origin".parse().unwrap(), "http://localhost:3000".parse().unwrap())
        .await;

    response.assert_status_ok();

    // Check that CORS header is present
    let headers = response.headers();
    assert!(
        headers.contains_key("access-control-allow-origin"),
        "Response should contain Access-Control-Allow-Origin header"
    );
}

/// Test that OPTIONS preflight request is handled correctly
#[tokio::test]
async fn test_cors_preflight_request() {
    let app = create_app();
    let server = TestServer::new(app).expect("Failed to create test server");

    // Make an OPTIONS preflight request
    let response = server
        .method(axum::http::Method::OPTIONS, "/health")
        .add_header("Origin".parse().unwrap(), "http://localhost:3000".parse().unwrap())
        .add_header(
            "Access-Control-Request-Method".parse().unwrap(),
            "GET".parse().unwrap(),
        )
        .await;

    // Preflight should return 200 or 204
    let status = response.status_code();
    assert!(
        status == axum::http::StatusCode::OK || status == axum::http::StatusCode::NO_CONTENT,
        "Preflight request should return 200 or 204, got {:?}",
        status
    );
}

/// Test that unknown routes return 404
#[tokio::test]
async fn test_unknown_route_returns_404() {
    let app = create_app();
    let server = TestServer::new(app).expect("Failed to create test server");

    let response = server.get("/nonexistent").await;

    response.assert_status_not_found();
}
