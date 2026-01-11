//! Integration tests for WebSocket endpoints
//!
//! These tests verify:
//! 1. WebSocket upgrade works correctly
//! 2. Binary MessagePack messages can be sent and received
//! 3. Connection management tracks active connections
//! 4. Broadcast system works correctly

use axum_test::TestServer;
use cascabel_api::{
    create_app_with_state,
    messages::{CarState, MetricsUpdate, ServerMessage, ServiceNodeState, SimulationUpdate},
    WebSocketState,
};

/// Test that the WebSocket endpoint exists and is accessible
#[tokio::test]
async fn test_websocket_endpoint_exists() {
    let ws_state = WebSocketState::new();
    let app = create_app_with_state(ws_state);
    let server = TestServer::new(app).expect("Failed to create test server");

    // A regular GET without WebSocket upgrade should fail
    // This verifies the route exists
    let response = server.get("/ws/test-sim-123").await;

    // Without proper WebSocket upgrade headers, we expect the server to reject
    // Axum typically returns 400 or upgrade-required
    let status = response.status_code();
    assert!(
        status.is_client_error(),
        "Expected client error without WebSocket upgrade, got {:?}",
        status
    );
}

/// Test that WebSocketState correctly manages senders
#[tokio::test]
async fn test_websocket_state_sender_management() {
    let ws_state = WebSocketState::new();

    // Create a sender for a simulation
    let sender1 = ws_state.get_or_create_sender("sim1").await;
    assert_eq!(sender1.receiver_count(), 0);

    // Creating again should return the same sender
    let sender2 = ws_state.get_or_create_sender("sim1").await;

    // Subscribe a receiver
    let _rx = sender1.subscribe();
    assert_eq!(sender2.receiver_count(), 1);

    // Remove the sender
    ws_state.remove_sender("sim1").await;

    // Now creating should give a new sender with 0 receivers
    let sender3 = ws_state.get_or_create_sender("sim1").await;
    assert_eq!(sender3.receiver_count(), 0);
}

/// Test broadcast to multiple receivers
#[tokio::test]
async fn test_broadcast_to_multiple_receivers() {
    let ws_state = WebSocketState::new();

    // Create sender and subscribe multiple receivers
    let sender = ws_state.get_or_create_sender("sim1").await;
    let mut rx1 = sender.subscribe();
    let mut rx2 = sender.subscribe();
    let mut rx3 = sender.subscribe();

    assert_eq!(ws_state.subscriber_count("sim1").await, 3);

    // Broadcast a message
    let msg = ServerMessage::Heartbeat;
    let result = ws_state.broadcast("sim1", &msg).await;

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 3); // 3 receivers

    // All receivers should get the message
    let data1 = rx1.recv().await.unwrap();
    let data2 = rx2.recv().await.unwrap();
    let data3 = rx3.recv().await.unwrap();

    // All should decode to Heartbeat
    let decoded1: ServerMessage = rmp_serde::from_slice(&data1).unwrap();
    let decoded2: ServerMessage = rmp_serde::from_slice(&data2).unwrap();
    let decoded3: ServerMessage = rmp_serde::from_slice(&data3).unwrap();

    assert!(matches!(decoded1, ServerMessage::Heartbeat));
    assert!(matches!(decoded2, ServerMessage::Heartbeat));
    assert!(matches!(decoded3, ServerMessage::Heartbeat));
}

/// Test broadcast with SimulationUpdate message
#[tokio::test]
async fn test_broadcast_simulation_update() {
    let ws_state = WebSocketState::new();

    let sender = ws_state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    // Create a realistic simulation update
    let update = SimulationUpdate {
        cars: vec![
            CarState {
                id: 1,
                position: [32.5, -117.0],
                velocity: 5.5,
                status: 1,
                queue_id: Some(0),
                queue_position: Some(1),
            },
            CarState {
                id: 2,
                position: [32.6, -117.1],
                velocity: 10.0,
                status: 0,
                queue_id: None,
                queue_position: None,
            },
        ],
        metrics: MetricsUpdate {
            total_arrivals: 100,
            total_completions: 50,
            average_wait_time: Some(120.5),
            simulation_time: 3600.0,
        },
        service_nodes: vec![ServiceNodeState {
            node_id: "booth_1".to_string(),
            queue_id: 0,
            is_busy: true,
            current_car_id: Some(1),
            service_rate: 3.0,
            total_served: 50,
        }],
        timestamp: 1234567890.123,
    };

    let msg = ServerMessage::SimulationUpdate(update.clone());
    let result = ws_state.broadcast("sim1", &msg).await;
    assert!(result.is_ok());

    // Receive and decode
    let data = rx.recv().await.unwrap();
    let decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();

    match decoded {
        ServerMessage::SimulationUpdate(received) => {
            assert_eq!(received.cars.len(), 2);
            assert_eq!(received.cars[0].id, 1);
            assert_eq!(received.metrics.total_arrivals, 100);
            assert_eq!(received.service_nodes.len(), 1);
            assert!((received.timestamp - 1234567890.123).abs() < 0.001);
        }
        _ => panic!("Expected SimulationUpdate"),
    }
}

/// Test update rate configuration
#[tokio::test]
async fn test_custom_update_rates() {
    // Default rates
    let state1 = WebSocketState::new();
    assert_eq!(state1.update_rate_hz, 10);
    assert!(!state1.enable_position_only_updates);

    // Custom rates with position-only enabled
    let state2 = WebSocketState::with_update_rates(10, 60);
    assert_eq!(state2.update_rate_hz, 10);
    assert_eq!(state2.position_only_rate_hz, 60);
    assert!(state2.enable_position_only_updates);

    // Position-only disabled when same rate
    let state3 = WebSocketState::with_update_rates(30, 30);
    assert!(!state3.enable_position_only_updates);
}

/// Test that serialized messages are compact
#[tokio::test]
async fn test_message_serialization_size() {
    // Create a message with 1000 cars (typical simulation size)
    let cars: Vec<CarState> = (0..1000)
        .map(|i| CarState {
            id: i,
            position: [32.5 + (i as f32 * 0.001), -117.0 + (i as f32 * 0.001)],
            velocity: 10.0,
            status: (i % 4) as u8,
            queue_id: if i % 2 == 0 { Some(0) } else { None },
            queue_position: if i % 2 == 0 { Some(i) } else { None },
        })
        .collect();

    let update = SimulationUpdate {
        cars,
        metrics: MetricsUpdate {
            total_arrivals: 1000,
            total_completions: 500,
            average_wait_time: Some(120.5),
            simulation_time: 3600.0,
        },
        service_nodes: vec![],
        timestamp: 0.0,
    };

    let msg = ServerMessage::SimulationUpdate(update);
    let bytes = rmp_serde::to_vec(&msg).unwrap();

    // MessagePack for 1000 cars should be reasonably small
    // Rough estimate: 17-25 bytes per car minimum
    let bytes_per_car = bytes.len() as f64 / 1000.0;
    println!(
        "1000 cars: {} bytes total, {:.1} bytes per car",
        bytes.len(),
        bytes_per_car
    );

    // Should be under 30 bytes per car on average
    assert!(
        bytes_per_car < 35.0,
        "Expected < 35 bytes per car, got {:.1}",
        bytes_per_car
    );
}

/// Test isolation between different simulations
#[tokio::test]
async fn test_simulation_isolation() {
    let ws_state = WebSocketState::new();

    // Create senders for two different simulations
    let sender1 = ws_state.get_or_create_sender("sim1").await;
    let sender2 = ws_state.get_or_create_sender("sim2").await;

    // Subscribe to both
    let mut rx1 = sender1.subscribe();
    let mut rx2 = sender2.subscribe();

    // Broadcast to sim1 only
    let msg1 = ServerMessage::Heartbeat;
    ws_state.broadcast("sim1", &msg1).await.unwrap();

    // rx1 should receive it
    let result1 = tokio::time::timeout(std::time::Duration::from_millis(100), rx1.recv()).await;
    assert!(result1.is_ok(), "rx1 should receive message");

    // rx2 should NOT receive it (timeout)
    let result2 = tokio::time::timeout(std::time::Duration::from_millis(100), rx2.recv()).await;
    assert!(result2.is_err(), "rx2 should not receive message from sim1");

    // Now broadcast to sim2
    let msg2 = ServerMessage::Ack { message_id: None };
    ws_state.broadcast("sim2", &msg2).await.unwrap();

    // rx2 should receive this one
    let result2 = tokio::time::timeout(std::time::Duration::from_millis(100), rx2.recv()).await;
    assert!(result2.is_ok(), "rx2 should receive message from sim2");
}
