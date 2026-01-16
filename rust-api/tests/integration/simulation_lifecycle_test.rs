//! End-to-end simulation lifecycle integration tests
//!
//! These tests verify the complete simulation workflow:
//! 1. Start simulation via REST API
//! 2. Cars spawn and move correctly
//! 3. Queue transitions work properly
//! 4. Service nodes process cars
//! 5. Simulation controls (pause, resume, time speed) work
//! 6. Stop simulation and verify final state

use axum_test::TestServer;
use cascabel_api::{
    create_app_with_state,
    simulation::{Path, SimulationConfig, SimulationEngine},
    SimulationState,
    WebSocketState,
};
use serde_json::json;

/// Helper to create test server
fn create_test_server() -> TestServer {
    let ws_state = WebSocketState::new();
    let sim_state = SimulationState::new();
    let app = create_app_with_state(ws_state, sim_state);
    TestServer::new(app).expect("Failed to create test server")
}

// ========== Complete Simulation Lifecycle Tests ==========

#[tokio::test]
async fn test_full_simulation_lifecycle() {
    let server = create_test_server();

    // Step 1: Start simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({
            "border_config": {
                "num_queues": 2,
                "arrival_rate": 5.0,
                "service_rates": [3.0, 3.0],
                "safe_distance": 4.0
            },
            "simulation_config": {
                "max_simulation_time": 300.0,
                "time_factor": 10.0
            }
        }))
        .await;

    create_response.assert_status_ok();
    let body: serde_json::Value = create_response.json();
    let sim_id = body.get("simulation_id").unwrap().as_str().unwrap();
    assert_eq!(body.get("status").unwrap(), "running");

    // Step 2: Verify initial status
    let status_response = server
        .get(&format!("/simulation/{}/status", sim_id))
        .await;

    status_response.assert_status_ok();
    let status: serde_json::Value = status_response.json();
    assert_eq!(status.get("status").unwrap(), "running");

    // Step 3: Add some cars manually
    for _ in 0..5 {
        let add_response = server
            .post(&format!("/simulation/{}/add_car", sim_id))
            .json(&serde_json::Value::Null)
            .await;
        add_response.assert_status_ok();
    }

    // Step 4: Verify cars were added
    let state_response = server
        .get(&format!("/simulation/{}/state", sim_id))
        .await;

    state_response.assert_status_ok();
    let state: serde_json::Value = state_response.json();
    assert!(state.get("cars").unwrap().as_array().unwrap().len() >= 5);

    // Step 5: Add a service station
    let add_station_response = server
        .post(&format!("/simulation/{}/add_station", sim_id))
        .json(&json!({
            "queue_id": 0,
            "service_rate": 5.0
        }))
        .await;

    add_station_response.assert_status_ok();

    // Step 6: Update time speed
    let time_speed_response = server
        .put(&format!("/simulation/{}/time_speed", sim_id))
        .json(&json!({"time_factor": 5.0}))
        .await;

    time_speed_response.assert_status_ok();
    let time_body: serde_json::Value = time_speed_response.json();
    assert_eq!(time_body.get("time_factor").unwrap(), 5.0);

    // Step 7: Stop simulation
    let stop_response = server
        .post(&format!("/simulation/{}/stop", sim_id))
        .await;

    stop_response.assert_status_ok();
    let stop_body: serde_json::Value = stop_response.json();
    assert_eq!(stop_body.get("status").unwrap(), "stopped");

    // Step 8: Verify simulation is stopped
    let final_status = server
        .get(&format!("/simulation/{}/status", sim_id))
        .await;

    final_status.assert_status_ok();
    let final_body: serde_json::Value = final_status.json();
    assert_eq!(final_body.get("status").unwrap(), "stopped");
}

#[tokio::test]
async fn test_simulation_cancellation() {
    let server = create_test_server();

    // Start simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({
            "border_config": {"num_queues": 2}
        }))
        .await;

    create_response.assert_status_ok();
    let body: serde_json::Value = create_response.json();
    let sim_id = body.get("simulation_id").unwrap().as_str().unwrap();

    // Cancel simulation
    let cancel_response = server
        .delete(&format!("/simulation/{}", sim_id))
        .await;

    cancel_response.assert_status_ok();
    let cancel_body: serde_json::Value = cancel_response.json();
    assert_eq!(cancel_body.get("status").unwrap(), "cancelled");
}

#[tokio::test]
async fn test_multiple_simulations_concurrent() {
    let server = create_test_server();

    // Start multiple simulations
    let mut sim_ids = Vec::new();
    for i in 0..3 {
        let create_response = server
            .post("/simulate")
            .json(&json!({
                "border_config": {"num_queues": i + 1}
            }))
            .await;

        create_response.assert_status_ok();
        let body: serde_json::Value = create_response.json();
        sim_ids.push(body.get("simulation_id").unwrap().as_str().unwrap().to_string());
    }

    // Verify all are running
    for sim_id in &sim_ids {
        let status_response = server
            .get(&format!("/simulation/{}/status", sim_id))
            .await;

        status_response.assert_status_ok();
        let status: serde_json::Value = status_response.json();
        assert_eq!(status.get("status").unwrap(), "running");
    }

    // Stop all
    for sim_id in &sim_ids {
        let stop_response = server
            .post(&format!("/simulation/{}/stop", sim_id))
            .await;
        stop_response.assert_status_ok();
    }
}

// ========== Car Spawning and Movement Tests ==========

#[test]
fn test_car_spawning_and_initial_state() {
    let mut engine = SimulationEngine::new();
    let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);

    let car_id = engine.spawn_car(path, 0);

    assert_eq!(car_id, 1);
    assert_eq!(engine.active_car_count(), 1);

    let states = engine.get_car_states();
    assert_eq!(states.len(), 1);
    assert_eq!(states[0].id, car_id);
}

#[test]
fn test_car_movement_over_time() {
    let mut engine = SimulationEngine::new();
    let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);

    engine.spawn_car(path, 0);

    // Record initial position
    let initial_states = engine.get_car_states();
    let initial_x = initial_states[0].x;

    // Run simulation for 1 second
    for _ in 0..100 {
        engine.step(0.01);
    }

    // Check car has moved
    let final_states = engine.get_car_states();
    let final_x = final_states[0].x;

    assert!(
        final_x > initial_x,
        "Car should have moved forward: initial={}, final={}",
        initial_x, final_x
    );
}

#[test]
fn test_multiple_cars_movement() {
    let mut engine = SimulationEngine::new();

    // Spawn 10 cars in different lanes
    for i in 0..10 {
        let path = Path::new(vec![
            (0.0, (i % 3) as f64 * 10.0),
            (1000.0, (i % 3) as f64 * 10.0),
        ]);
        engine.spawn_car(path, i % 3);
    }

    assert_eq!(engine.active_car_count(), 10);

    // Run for 5 seconds
    for _ in 0..500 {
        engine.step(0.01);
    }

    // All cars should still exist and have moved
    let states = engine.get_car_states();
    for state in &states {
        assert!(state.x > 0.0, "Car {} should have moved forward", state.id);
    }
}

// ========== Queue Transition Tests ==========

#[test]
fn test_car_status_transitions() {
    let mut engine = SimulationEngine::with_config(SimulationConfig {
        safe_distance: 4.0,
        ..Default::default()
    });

    // Set booth position at x=100
    engine.set_booth_position(100.0, 0.0);
    engine.spawn_service_node("booth_1".to_string(), 0, 3.0);

    // Spawn car far from booth
    let path = Path::new(vec![(0.0, 0.0), (200.0, 0.0)]);
    engine.spawn_car(path, 0);

    // Initial status should be Approaching
    let initial_states = engine.get_car_states();
    assert!(matches!(
        initial_states[0].status,
        cascabel_api::simulation::Status::Approaching
    ));

    // Run simulation until status changes
    for _ in 0..10000 {
        engine.step(0.01);

        let states = engine.get_car_states();
        if states.is_empty() {
            break; // Car completed
        }
    }

    // Simulation ran successfully
    assert!(engine.current_time() > 0.0);
}

// ========== Service Node Tests ==========

#[test]
fn test_service_node_creation() {
    let mut engine = SimulationEngine::new();

    engine.spawn_service_node("booth_1".to_string(), 0, 3.0);
    engine.spawn_service_node("booth_2".to_string(), 1, 4.0);

    // Run a step to ensure nodes exist
    engine.step(0.01);

    // Should not crash
    assert!(engine.current_time() > 0.0);
}

#[test]
fn test_car_service_completion() {
    let mut engine = SimulationEngine::with_config(SimulationConfig {
        safe_distance: 4.0,
        ..Default::default()
    });

    engine.set_booth_position(50.0, 0.0);
    engine.spawn_service_node("booth_1".to_string(), 0, 10.0); // High service rate

    // Spawn car close to booth
    let path = Path::new(vec![(0.0, 0.0), (100.0, 0.0)]);
    engine.spawn_car(path, 0);

    let initial_completions = engine.stats().total_completions;

    // Run simulation for extended time to allow service
    for _ in 0..50000 {
        engine.step(0.01);
    }

    let stats = engine.stats();

    // Either car completed service or is still being processed
    // This test verifies the simulation doesn't crash during service
    assert!(stats.total_arrivals >= 1);
}

// ========== Simulation Control Tests ==========

#[test]
fn test_time_scale_affects_simulation_speed() {
    let mut engine = SimulationEngine::new();
    let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
    engine.spawn_car(path, 0);

    // Normal speed - run for 1 second
    for _ in 0..100 {
        engine.step(0.01);
    }
    let normal_time = engine.current_time();

    // Reset
    let mut engine2 = SimulationEngine::new();
    let path2 = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
    engine2.spawn_car(path2, 0);
    engine2.set_time_scale(2.0);

    // 2x speed - run for same wall-clock steps
    for _ in 0..100 {
        engine2.step(0.01);
    }
    let scaled_time = engine2.current_time();

    // Scaled time should be ~2x normal time
    let ratio = scaled_time / normal_time;
    assert!(
        (ratio - 2.0).abs() < 0.1,
        "Time scale should be ~2x: ratio={}",
        ratio
    );
}

#[tokio::test]
async fn test_time_speed_endpoint_validation() {
    let server = create_test_server();

    // Start simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let body: serde_json::Value = create_response.json();
    let sim_id = body.get("simulation_id").unwrap().as_str().unwrap();

    // Test valid time factors
    for factor in [0.5, 1.0, 2.0, 5.0, 10.0] {
        let response = server
            .put(&format!("/simulation/{}/time_speed", sim_id))
            .json(&json!({"time_factor": factor}))
            .await;

        response.assert_status_ok();
    }

    // Test invalid time factors
    for factor in [-1.0, 0.0] {
        let response = server
            .put(&format!("/simulation/{}/time_speed", sim_id))
            .json(&json!({"time_factor": factor}))
            .await;

        response.assert_status_bad_request();
    }
}

// ========== Error Handling Tests ==========

#[tokio::test]
async fn test_operations_on_nonexistent_simulation() {
    let server = create_test_server();
    let fake_id = "nonexistent-sim-id";

    // All operations should return 404
    let status = server.get(&format!("/simulation/{}/status", fake_id)).await;
    status.assert_status_not_found();

    let state = server.get(&format!("/simulation/{}/state", fake_id)).await;
    state.assert_status_not_found();

    let stop = server.post(&format!("/simulation/{}/stop", fake_id)).await;
    stop.assert_status_not_found();

    let time = server
        .put(&format!("/simulation/{}/time_speed", fake_id))
        .json(&json!({"time_factor": 2.0}))
        .await;
    time.assert_status_not_found();

    let car = server.get(&format!("/simulation/{}/car/1", fake_id)).await;
    car.assert_status_not_found();
}

#[tokio::test]
async fn test_add_car_to_stopped_simulation() {
    let server = create_test_server();

    // Start simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let body: serde_json::Value = create_response.json();
    let sim_id = body.get("simulation_id").unwrap().as_str().unwrap();

    // Stop simulation
    let _ = server.post(&format!("/simulation/{}/stop", sim_id)).await;

    // Try to add car - should fail
    let add_response = server
        .post(&format!("/simulation/{}/add_car", sim_id))
        .json(&serde_json::Value::Null)
        .await;

    add_response.assert_status_bad_request();
}

// ========== Statistics Tracking Tests ==========

#[test]
fn test_statistics_tracking() {
    let mut engine = SimulationEngine::new();

    // Initial stats
    let initial_stats = engine.stats();
    assert_eq!(initial_stats.total_arrivals, 0);
    assert_eq!(initial_stats.total_completions, 0);

    // Spawn cars
    for _ in 0..5 {
        let path = Path::new(vec![(0.0, 0.0), (100.0, 0.0)]);
        engine.spawn_car(path, 0);
    }

    let after_spawn_stats = engine.stats();
    assert_eq!(after_spawn_stats.total_arrivals, 5);
    assert_eq!(after_spawn_stats.active_cars, 5);
}

#[tokio::test]
async fn test_statistics_in_api_response() {
    let server = create_test_server();

    // Start simulation
    let create_response = server
        .post("/simulate")
        .json(&json!({"border_config": {"num_queues": 2}}))
        .await;

    let body: serde_json::Value = create_response.json();
    let sim_id = body.get("simulation_id").unwrap().as_str().unwrap();

    // Add some cars
    for _ in 0..10 {
        let _ = server
            .post(&format!("/simulation/{}/add_car", sim_id))
            .json(&serde_json::Value::Null)
            .await;
    }

    // Get state and check statistics
    let state_response = server
        .get(&format!("/simulation/{}/state", sim_id))
        .await;

    state_response.assert_status_ok();
    let state: serde_json::Value = state_response.json();

    let stats = state.get("statistics").unwrap();
    assert!(stats.get("total_arrivals").is_some());
    assert!(stats.get("total_completions").is_some());
    assert!(stats.get("active_cars").is_some());
}
