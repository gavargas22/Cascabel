//! Integration tests for REST API endpoints
//!
//! These tests verify API parity with the FastAPI implementation
//! to ensure frontend compatibility.

use axum_test::TestServer;
use cascabel_api::{SimulationState, WebSocketState, create_app_with_state};
use serde_json::json;

/// Helper to create test server
fn create_test_server() -> TestServer {
    let ws_state = WebSocketState::new();
    let sim_state = SimulationState::new();
    let app = create_app_with_state(ws_state, sim_state);
    TestServer::new(app).expect("Failed to create test server")
}

// ========== POST /simulate Tests ==========

#[tokio::test]
async fn test_simulate_endpoint_basic() {
    let server = create_test_server();

    let request_body = json!({
        "border_config": {
            "num_queues": 2
        }
    });

    let response = server
        .post("/simulate")
        .json(&request_body)
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert!(body.get("simulation_id").is_some());
    assert_eq!(body.get("status").unwrap(), "running");
    assert!(body.get("websocket_url").is_some());
    assert!(body.get("message").is_some());
}

#[tokio::test]
async fn test_simulate_endpoint_with_full_config() {
    let server = create_test_server();

    let request_body = json!({
        "border_config": {
            "num_queues": 3,
            "nodes_per_queue": [2, 2, 2],
            "arrival_rate": 5.0,
            "service_rates": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
            "queue_assignment": "shortest",
            "safe_distance": 5.0,
            "max_queue_length": 30
        },
        "simulation_config": {
            "max_simulation_time": 7200.0,
            "time_factor": 2.0,
            "enable_telemetry": true,
            "enable_position_tracking": true
        },
        "crossing_name": "paso_del_norte",
        "direction": "mx2usa"
    });

    let response = server
        .post("/simulate")
        .json(&request_body)
        .await;

    response.assert_status_ok();
}

#[tokio::test]
async fn test_simulate_endpoint_with_physics_ranges() {
    let server = create_test_server();

    let request_body = json!({
        "border_config": {
            "num_queues": 2
        },
        "physics_ranges": {
            "speed_range": [10.0, 15.0],
            "safe_distance_range": [3.0, 6.0],
            "acceleration_range": [0.5, 1.0],
            "deceleration_range": [1.0, 1.5],
            "queue_spacing_range": [5.0, 10.0]
        }
    });

    let response = server
        .post("/simulate")
        .json(&request_body)
        .await;

    response.assert_status_ok();
}

// ========== GET /simulation/{id}/status Tests ==========

#[tokio::test]
async fn test_simulation_status_not_found() {
    let server = create_test_server();

    let response = server
        .get("/simulation/nonexistent-id/status")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_simulation_status_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    create_response.assert_status_ok();
    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Now get status
    let status_response = server
        .get(&format!("/simulation/{}/status", sim_id))
        .await;

    status_response.assert_status_ok();

    let status_body: serde_json::Value = status_response.json();
    assert_eq!(status_body.get("simulation_id").unwrap(), sim_id);
    assert_eq!(status_body.get("status").unwrap(), "running");
    assert!(status_body.get("progress").is_some());
    assert!(status_body.get("current_time").is_some());
    assert!(status_body.get("total_arrivals").is_some());
    assert!(status_body.get("total_completions").is_some());
}

// ========== GET /simulation/{id}/state Tests ==========

#[tokio::test]
async fn test_simulation_state_not_found() {
    let server = create_test_server();

    let response = server
        .get("/simulation/nonexistent-id/state")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_simulation_state_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Now get state
    let state_response = server
        .get(&format!("/simulation/{}/state", sim_id))
        .await;

    state_response.assert_status_ok();

    let state_body: serde_json::Value = state_response.json();
    assert_eq!(state_body.get("simulation_id").unwrap(), sim_id);
    assert!(state_body.get("cars").is_some());
    assert!(state_body.get("service_nodes").is_some());
    assert!(state_body.get("statistics").is_some());
}

// ========== POST /simulation/{id}/stop Tests ==========

#[tokio::test]
async fn test_stop_simulation_not_found() {
    let server = create_test_server();

    let response = server
        .post("/simulation/nonexistent-id/stop")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_stop_simulation_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Now stop it
    let stop_response = server
        .post(&format!("/simulation/{}/stop", sim_id))
        .await;

    stop_response.assert_status_ok();

    let stop_body: serde_json::Value = stop_response.json();
    assert_eq!(stop_body.get("simulation_id").unwrap(), sim_id);
    assert_eq!(stop_body.get("status").unwrap(), "stopped");
}

// ========== DELETE /simulation/{id} Tests ==========

#[tokio::test]
async fn test_cancel_simulation_not_found() {
    let server = create_test_server();

    let response = server
        .delete("/simulation/nonexistent-id")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_cancel_simulation_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Now cancel it
    let cancel_response = server
        .delete(&format!("/simulation/{}", sim_id))
        .await;

    cancel_response.assert_status_ok();

    let cancel_body: serde_json::Value = cancel_response.json();
    assert_eq!(cancel_body.get("simulation_id").unwrap(), sim_id);
    assert_eq!(cancel_body.get("status").unwrap(), "cancelled");
}

// ========== PUT /simulation/{id}/time_speed Tests ==========

#[tokio::test]
async fn test_time_speed_not_found() {
    let server = create_test_server();

    let response = server
        .put("/simulation/nonexistent-id/time_speed")
        .json(&json!({"time_factor": 2.0}))
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_time_speed_invalid_factor() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Try invalid time factor
    let response = server
        .put(&format!("/simulation/{}/time_speed", sim_id))
        .json(&json!({"time_factor": -1.0}))
        .await;

    response.assert_status_bad_request();
}

#[tokio::test]
async fn test_time_speed_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Update time speed
    let response = server
        .put(&format!("/simulation/{}/time_speed", sim_id))
        .json(&json!({"time_factor": 2.0}))
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert_eq!(body.get("status").unwrap(), "updated");
    assert_eq!(body.get("time_factor").unwrap(), 2.0);
}

// ========== POST /simulation/{id}/add_station Tests ==========

#[tokio::test]
async fn test_add_station_not_found() {
    let server = create_test_server();

    let response = server
        .post("/simulation/nonexistent-id/add_station")
        .json(&json!({"queue_id": 0, "service_rate": 3.0}))
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_add_station_invalid_queue() {
    let server = create_test_server();

    // First create a simulation with 2 queues
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Try to add station to queue 5 (doesn't exist)
    let response = server
        .post(&format!("/simulation/{}/add_station", sim_id))
        .json(&json!({"queue_id": 5, "service_rate": 3.0}))
        .await;

    response.assert_status_bad_request();
}

#[tokio::test]
async fn test_add_station_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Add station
    let response = server
        .post(&format!("/simulation/{}/add_station", sim_id))
        .json(&json!({
            "queue_id": 0,
            "service_rate": 4.0,
            "service_time_variation": 0.25
        }))
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert!(body.get("station_id").is_some());
    assert_eq!(body.get("queue_id").unwrap(), 0);
    assert_eq!(body.get("service_rate").unwrap(), 4.0);
}

// ========== DELETE /simulation/{id}/service_node/{node_id} Tests ==========

#[tokio::test]
async fn test_remove_service_node_not_found() {
    let server = create_test_server();

    let response = server
        .delete("/simulation/nonexistent-id/service_node/node123")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_remove_service_node_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Remove a node (will succeed even if node doesn't exist in current implementation)
    let response = server
        .delete(&format!("/simulation/{}/service_node/test_node", sim_id))
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert_eq!(body.get("node_id").unwrap(), "test_node");
    assert!(body.get("message").is_some());
}

// ========== POST /simulation/{id}/add_car Tests ==========

#[tokio::test]
async fn test_add_car_not_found() {
    let server = create_test_server();

    let response = server
        .post("/simulation/nonexistent-id/add_car")
        .json(&serde_json::Value::Null)
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_add_car_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Add a car
    let response = server
        .post(&format!("/simulation/{}/add_car", sim_id))
        .json(&serde_json::Value::Null)
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert!(body.get("car_id").is_some());
    assert!(body.get("queue_id").is_some());
    assert!(body.get("message").is_some());
}

// ========== GET /simulation/{id}/car/{car_id} Tests ==========

#[tokio::test]
async fn test_get_car_simulation_not_found() {
    let server = create_test_server();

    let response = server
        .get("/simulation/nonexistent-id/car/1")
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_get_car_not_found() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Try to get non-existent car
    let response = server
        .get(&format!("/simulation/{}/car/999", sim_id))
        .await;

    response.assert_status_not_found();
}

#[tokio::test]
async fn test_get_car_success() {
    let server = create_test_server();

    // First create a simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let create_body: serde_json::Value = create_response.json();
    let sim_id = create_body.get("simulation_id").unwrap().as_str().unwrap();

    // Add a car
    let add_response = server
        .post(&format!("/simulation/{}/add_car", sim_id))
        .json(&serde_json::Value::Null)
        .await;

    let add_body: serde_json::Value = add_response.json();
    let car_id = add_body.get("car_id").unwrap().as_u64().unwrap();

    // Get car details
    let response = server
        .get(&format!("/simulation/{}/car/{}", sim_id, car_id))
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert_eq!(body.get("car_id").unwrap().as_u64().unwrap(), car_id);
    assert!(body.get("status").is_some());
    assert!(body.get("position").is_some());
    assert!(body.get("velocity").is_some());
}

// ========== GET /border-crossings Tests ==========

#[tokio::test]
async fn test_get_border_crossings() {
    let server = create_test_server();

    let response = server
        .get("/border-crossings")
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert!(body.get("crossings").is_some());
}

// ========== GET /crossing/{name}/config Tests ==========

#[tokio::test]
async fn test_get_crossing_config_paso_del_norte() {
    let server = create_test_server();

    let response = server
        .get("/crossing/paso_del_norte/config")
        .await;

    // May be 200 or 404 depending on working directory
    let status = response.status_code();
    assert!(status.is_success() || status.as_u16() == 404);

    if status.is_success() {
        let body: serde_json::Value = response.json();
        assert!(body.get("bounding_box").is_some());
    }
}

#[tokio::test]
async fn test_get_crossing_config_not_found() {
    let server = create_test_server();

    let response = server
        .get("/crossing/nonexistent_crossing/config")
        .await;

    response.assert_status_not_found();
}

// ========== GET /geojson/{path} Tests ==========

#[tokio::test]
async fn test_get_geojson_not_found() {
    let server = create_test_server();

    let response = server
        .get("/geojson/nonexistent/path")
        .await;

    response.assert_status_not_found();
}

// ========== Health Check ==========

#[tokio::test]
async fn test_health_check() {
    let server = create_test_server();

    let response = server
        .get("/health")
        .await;

    response.assert_status_ok();

    let body: serde_json::Value = response.json();
    assert_eq!(body.get("status").unwrap(), "healthy");
    assert!(body.get("version").is_some());
    assert!(body.get("service").is_some());
}
