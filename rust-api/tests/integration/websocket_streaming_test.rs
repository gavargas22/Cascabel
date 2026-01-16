//! WebSocket streaming integration tests
//!
//! These tests verify:
//! 1. WebSocket connections can be established
//! 2. Binary MessagePack messages are properly serialized
//! 3. Multiple concurrent connections work correctly
//! 4. Broadcast system handles high load
//! 5. Message latency meets targets (<100ms)

use cascabel_api::{
    messages::{
        CarState, ClientMessage, ControlMessage, MetricsUpdate, PositionOnlyUpdate, ServerMessage,
        ServiceNodeState, SimulationUpdate,
    },
    WebSocketState,
};
use std::time::{Duration, Instant};

// ========== WebSocket State Management Tests ==========

#[tokio::test]
async fn test_websocket_state_concurrent_access() {
    let state = WebSocketState::new();

    // Spawn multiple tasks that create and use senders
    let mut handles = vec![];

    for i in 0..10 {
        let state_clone = state.clone();
        let handle = tokio::spawn(async move {
            let sim_id = format!("sim_{}", i);
            let sender = state_clone.get_or_create_sender(&sim_id).await;

            // Subscribe and send messages
            let mut rx = sender.subscribe();
            let msg = ServerMessage::Heartbeat;

            for _ in 0..100 {
                let _ = state_clone.broadcast(&sim_id, &msg).await;
            }

            // Consume messages
            let mut count = 0;
            while let Ok(_) = tokio::time::timeout(Duration::from_millis(10), rx.recv()).await {
                count += 1;
            }

            count
        });

        handles.push(handle);
    }

    // Wait for all tasks to complete
    for handle in handles {
        let count = handle.await.unwrap();
        assert!(count > 0, "Each simulation should have received messages");
    }
}

#[tokio::test]
async fn test_websocket_broadcast_ordering() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    // Send numbered messages
    for i in 0..100 {
        let msg = ServerMessage::Ack {
            message_id: Some(format!("msg_{}", i)),
        };
        let _ = state.broadcast("sim1", &msg).await;
    }

    // Verify ordering is preserved
    for i in 0..100 {
        let data = tokio::time::timeout(Duration::from_millis(100), rx.recv())
            .await
            .expect("Should receive message")
            .expect("Channel should be open");

        let msg: ServerMessage = rmp_serde::from_slice(&data).unwrap();
        match msg {
            ServerMessage::Ack { message_id } => {
                assert_eq!(message_id, Some(format!("msg_{}", i)));
            }
            _ => panic!("Expected Ack message"),
        }
    }
}

// ========== Message Serialization Tests ==========

#[test]
fn test_simulation_update_round_trip() {
    let update = SimulationUpdate {
        cars: (0..100)
            .map(|i| CarState {
                id: i,
                position: [32.5 + (i as f32 * 0.001), -117.0 + (i as f32 * 0.001)],
                velocity: 10.0 + (i as f32 * 0.1),
                status: (i % 4) as u8,
                queue_id: if i % 2 == 0 { Some(i % 3) } else { None },
                queue_position: if i % 2 == 0 { Some(i) } else { None },
            })
            .collect(),
        metrics: MetricsUpdate {
            total_arrivals: 500,
            total_completions: 250,
            average_wait_time: Some(120.5),
            simulation_time: 1800.0,
        },
        service_nodes: vec![
            ServiceNodeState {
                node_id: "booth_1".to_string(),
                queue_id: 0,
                is_busy: true,
                current_car_id: Some(1),
                service_rate: 3.0,
                total_served: 125,
            },
            ServiceNodeState {
                node_id: "booth_2".to_string(),
                queue_id: 1,
                is_busy: false,
                current_car_id: None,
                service_rate: 4.0,
                total_served: 125,
            },
        ],
        timestamp: 1234567890.123,
    };

    let msg = ServerMessage::SimulationUpdate(update.clone());

    // Serialize to MessagePack
    let bytes = rmp_serde::to_vec(&msg).unwrap();

    // Deserialize
    let decoded: ServerMessage = rmp_serde::from_slice(&bytes).unwrap();

    match decoded {
        ServerMessage::SimulationUpdate(received) => {
            assert_eq!(received.cars.len(), 100);
            assert_eq!(received.metrics.total_arrivals, 500);
            assert_eq!(received.service_nodes.len(), 2);
            assert!((received.timestamp - 1234567890.123).abs() < 0.001);
        }
        _ => panic!("Expected SimulationUpdate"),
    }
}

#[test]
fn test_position_only_update_round_trip() {
    let update = PositionOnlyUpdate {
        positions: (0..1000)
            .map(|i| (i as u32, 32.5_f32 + (i as f32 * 0.0001), -117.0_f32 + (i as f32 * 0.0001)))
            .collect(),
        timestamp: 1234567890.456,
    };

    let msg = ServerMessage::PositionOnly(update.clone());
    let bytes = rmp_serde::to_vec(&msg).unwrap();
    let decoded: ServerMessage = rmp_serde::from_slice(&bytes).unwrap();

    match decoded {
        ServerMessage::PositionOnly(received) => {
            assert_eq!(received.positions.len(), 1000);
            assert_eq!(received.positions[0].0, 0);
            assert_eq!(received.positions[999].0, 999);
        }
        _ => panic!("Expected PositionOnly"),
    }
}

#[test]
fn test_control_message_round_trip() {
    let control_messages = vec![
        ClientMessage::Control(ControlMessage::Pause),
        ClientMessage::Control(ControlMessage::Resume),
        ClientMessage::Control(ControlMessage::SetTimeSpeed { speed: 2.5 }),
        ClientMessage::Control(ControlMessage::AddStation { queue_id: 1 }),
        ClientMessage::Control(ControlMessage::RemoveStation {
            node_id: "booth_1".to_string(),
        }),
        ClientMessage::Heartbeat,
        ClientMessage::RequestFullState,
    ];

    for msg in control_messages {
        let bytes = rmp_serde::to_vec(&msg).unwrap();
        let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
        assert_eq!(msg, decoded);
    }
}

// ========== Latency Tests ==========

#[tokio::test]
async fn test_broadcast_latency() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    // Create a typical update with 1000 cars
    let update = SimulationUpdate {
        cars: (0..1000)
            .map(|i| CarState {
                id: i,
                position: [32.5 + (i as f32 * 0.0001), -117.0 + (i as f32 * 0.0001)],
                velocity: 10.0,
                status: (i % 4) as u8,
                queue_id: Some(i % 3),
                queue_position: Some(i),
            })
            .collect(),
        metrics: MetricsUpdate {
            total_arrivals: 1000,
            total_completions: 500,
            average_wait_time: Some(120.0),
            simulation_time: 3600.0,
        },
        service_nodes: vec![],
        timestamp: 0.0,
    };

    let msg = ServerMessage::SimulationUpdate(update);

    // Measure broadcast latency over multiple iterations
    let iterations = 100;
    let mut latencies = Vec::with_capacity(iterations);

    for _ in 0..iterations {
        let start = Instant::now();

        let _ = state.broadcast("sim1", &msg).await;
        let data = rx.recv().await.unwrap();
        let _decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();

        let latency = start.elapsed();
        latencies.push(latency);
    }

    // Calculate statistics
    let total: Duration = latencies.iter().sum();
    let avg = total / iterations as u32;
    let max = *latencies.iter().max().unwrap();
    let min = *latencies.iter().min().unwrap();

    println!(
        "Broadcast latency (1000 cars): avg={:?}, min={:?}, max={:?}",
        avg, min, max
    );

    // Target: <100ms per update
    assert!(
        avg < Duration::from_millis(100),
        "Average broadcast latency ({:?}) should be <100ms",
        avg
    );

    assert!(
        max < Duration::from_millis(200),
        "Max broadcast latency ({:?}) should be <200ms",
        max
    );
}

#[tokio::test]
async fn test_broadcast_latency_5000_cars() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    // Create update with 5000 cars (target load)
    let update = SimulationUpdate {
        cars: (0..5000)
            .map(|i| CarState {
                id: i,
                position: [32.5 + (i as f32 * 0.00002), -117.0 + (i as f32 * 0.00002)],
                velocity: 10.0 + (i as f32 * 0.001),
                status: (i % 4) as u8,
                queue_id: if i % 2 == 0 { Some(i % 3) } else { None },
                queue_position: if i % 2 == 0 { Some(i) } else { None },
            })
            .collect(),
        metrics: MetricsUpdate {
            total_arrivals: 5000,
            total_completions: 2500,
            average_wait_time: Some(150.0),
            simulation_time: 7200.0,
        },
        service_nodes: (0..10)
            .map(|i| ServiceNodeState {
                node_id: format!("booth_{}", i),
                queue_id: i % 3,
                is_busy: i % 2 == 0,
                current_car_id: if i % 2 == 0 { Some(i) } else { None },
                service_rate: 3.0,
                total_served: 250,
            })
            .collect(),
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs_f64(),
    };

    let msg = ServerMessage::SimulationUpdate(update);

    // Measure over multiple iterations
    let iterations = 50;
    let mut latencies = Vec::with_capacity(iterations);

    for _ in 0..iterations {
        let start = Instant::now();

        let _ = state.broadcast("sim1", &msg).await;
        let data = rx.recv().await.unwrap();
        let _decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();

        let latency = start.elapsed();
        latencies.push(latency);
    }

    let total: Duration = latencies.iter().sum();
    let avg = total / iterations as u32;
    let max = *latencies.iter().max().unwrap();

    println!(
        "Broadcast latency (5000 cars): avg={:?}, max={:?}",
        avg, max
    );

    // Target: <100ms even with 5000 cars
    assert!(
        avg < Duration::from_millis(100),
        "Average broadcast latency ({:?}) should be <100ms for 5000 cars",
        avg
    );
}

#[tokio::test]
async fn test_position_only_latency() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    // Position-only update for 5000 cars
    let update = PositionOnlyUpdate {
        positions: (0..5000)
            .map(|i| {
                (
                    i as u32,
                    32.5_f32 + (i as f32 * 0.00002),
                    -117.0_f32 + (i as f32 * 0.00002),
                )
            })
            .collect(),
        timestamp: 0.0,
    };

    let msg = ServerMessage::PositionOnly(update);

    // Measure latency
    let iterations = 100;
    let mut latencies = Vec::with_capacity(iterations);

    for _ in 0..iterations {
        let start = Instant::now();

        let _ = state.broadcast("sim1", &msg).await;
        let data = rx.recv().await.unwrap();
        let _decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();

        latencies.push(start.elapsed());
    }

    let total: Duration = latencies.iter().sum();
    let avg = total / iterations as u32;

    println!("Position-only latency (5000 cars): avg={:?}", avg);

    // Position-only should be faster
    assert!(
        avg < Duration::from_millis(50),
        "Position-only latency ({:?}) should be <50ms",
        avg
    );
}

// ========== Multiple Subscribers Tests ==========

#[tokio::test]
async fn test_multiple_subscribers_receive_updates() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;

    // Create 10 subscribers
    let mut receivers: Vec<_> = (0..10).map(|_| sender.subscribe()).collect();

    assert_eq!(state.subscriber_count("sim1").await, 10);

    // Broadcast a message
    let msg = ServerMessage::Heartbeat;
    let result = state.broadcast("sim1", &msg).await;

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 10);

    // All receivers should get the message
    for rx in receivers.iter_mut() {
        let data = tokio::time::timeout(Duration::from_millis(100), rx.recv())
            .await
            .expect("Receiver should get message")
            .expect("Channel should be open");

        let decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();
        assert!(matches!(decoded, ServerMessage::Heartbeat));
    }
}

#[tokio::test]
async fn test_subscriber_disconnection() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;

    // Create and immediately drop some subscribers
    {
        let _rx1 = sender.subscribe();
        let _rx2 = sender.subscribe();
        assert_eq!(state.subscriber_count("sim1").await, 2);
    }

    // After drop, subscriber count should be 0
    assert_eq!(state.subscriber_count("sim1").await, 0);

    // Broadcast should fail with no receivers
    let msg = ServerMessage::Heartbeat;
    let result = state.broadcast("sim1", &msg).await;
    assert!(result.is_err());
}

// ========== High Throughput Tests ==========

#[tokio::test]
async fn test_high_frequency_updates() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    let update = SimulationUpdate {
        cars: (0..100)
            .map(|i| CarState {
                id: i,
                position: [32.5, -117.0],
                velocity: 10.0,
                status: 1,
                queue_id: Some(0),
                queue_position: Some(i),
            })
            .collect(),
        metrics: MetricsUpdate {
            total_arrivals: 100,
            total_completions: 50,
            average_wait_time: Some(60.0),
            simulation_time: 300.0,
        },
        service_nodes: vec![],
        timestamp: 0.0,
    };

    let msg = ServerMessage::SimulationUpdate(update);

    // Send 10Hz updates for 1 second (10 updates)
    let start = Instant::now();
    for _ in 0..10 {
        let _ = state.broadcast("sim1", &msg).await;
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    let duration = start.elapsed();

    // Consume all messages
    let mut received = 0;
    while let Ok(result) = tokio::time::timeout(Duration::from_millis(50), rx.recv()).await {
        if result.is_ok() {
            received += 1;
        }
    }

    println!("Received {} messages in {:?}", received, duration);
    assert!(received >= 10, "Should receive all 10 updates");
}

#[tokio::test]
async fn test_30hz_position_updates() {
    let state = WebSocketState::new();
    let sender = state.get_or_create_sender("sim1").await;
    let mut rx = sender.subscribe();

    let update = PositionOnlyUpdate {
        positions: (0..1000).map(|i| (i as u32, 32.5, -117.0)).collect(),
        timestamp: 0.0,
    };

    let msg = ServerMessage::PositionOnly(update);

    // Send at 30Hz for 1 second (30 updates)
    let start = Instant::now();
    for _ in 0..30 {
        let _ = state.broadcast("sim1", &msg).await;
        tokio::time::sleep(Duration::from_micros(33333)).await; // ~30Hz
    }
    let duration = start.elapsed();

    // Consume all messages
    let mut received = 0;
    while let Ok(result) = tokio::time::timeout(Duration::from_millis(50), rx.recv()).await {
        if result.is_ok() {
            received += 1;
        }
    }

    println!("Received {} position updates in {:?}", received, duration);
    assert!(
        received >= 28,
        "Should receive nearly all 30 updates, got {}",
        received
    );
}

// ========== Message Size Verification Tests ==========

#[test]
fn test_message_size_5000_cars() {
    let update = SimulationUpdate {
        cars: (0..5000)
            .map(|i| CarState {
                id: i,
                position: [32.5 + (i as f32 * 0.00002), -117.0 + (i as f32 * 0.00002)],
                velocity: 10.0 + (i as f32 * 0.001),
                status: (i % 4) as u8,
                queue_id: if i % 2 == 0 { Some(i % 3) } else { None },
                queue_position: if i % 2 == 0 { Some(i) } else { None },
            })
            .collect(),
        metrics: MetricsUpdate {
            total_arrivals: 5000,
            total_completions: 2500,
            average_wait_time: Some(180.0),
            simulation_time: 7200.0,
        },
        service_nodes: (0..10)
            .map(|i| ServiceNodeState {
                node_id: format!("booth_{}", i),
                queue_id: i % 3,
                is_busy: i % 2 == 0,
                current_car_id: if i % 2 == 0 { Some(i) } else { None },
                service_rate: 3.0,
                total_served: 500,
            })
            .collect(),
        timestamp: 1234567890.123,
    };

    let msg = ServerMessage::SimulationUpdate(update);

    let msgpack_bytes = rmp_serde::to_vec(&msg).unwrap();
    let json_bytes = serde_json::to_vec(&msg).unwrap();

    let ratio = msgpack_bytes.len() as f64 / json_bytes.len() as f64;
    let bytes_per_car = msgpack_bytes.len() as f64 / 5000.0;

    println!("5000 cars - MessagePack: {} bytes ({:.2} KB)", msgpack_bytes.len(), msgpack_bytes.len() as f64 / 1024.0);
    println!("5000 cars - JSON: {} bytes ({:.2} KB)", json_bytes.len(), json_bytes.len() as f64 / 1024.0);
    println!("MessagePack is {:.1}% of JSON size ({:.1}% savings)", ratio * 100.0, (1.0 - ratio) * 100.0);
    println!("Bytes per car: {:.1}", bytes_per_car);

    // Verify MessagePack is at least 40% smaller than JSON
    assert!(
        ratio < 0.6,
        "MessagePack should be <60% of JSON size, but is {:.1}%",
        ratio * 100.0
    );

    // Verify bytes per car is reasonable
    assert!(
        bytes_per_car < 35.0,
        "Should be <35 bytes per car, got {:.1}",
        bytes_per_car
    );
}

#[test]
fn test_position_only_size_5000_cars() {
    let update = PositionOnlyUpdate {
        positions: (0..5000)
            .map(|i| (i as u32, 32.5_f32 + (i as f32 * 0.00002), -117.0_f32 + (i as f32 * 0.00002)))
            .collect(),
        timestamp: 1234567890.123,
    };

    let msg = ServerMessage::PositionOnly(update);
    let bytes = rmp_serde::to_vec(&msg).unwrap();

    let bytes_per_position = bytes.len() as f64 / 5000.0;

    println!("Position-only (5000): {} bytes ({:.2} KB)", bytes.len(), bytes.len() as f64 / 1024.0);
    println!("Bytes per position: {:.1}", bytes_per_position);

    // Position-only should be very compact: ~12 bytes per position
    // (4 bytes id + 4 bytes lat + 4 bytes lon)
    assert!(
        bytes_per_position < 15.0,
        "Position-only should be <15 bytes per car, got {:.1}",
        bytes_per_position
    );
}

// ========== End-to-End WebSocket Streaming Tests ==========

/// Test the complete streaming flow: start simulation, receive updates, stop
#[tokio::test]
async fn test_e2e_simulation_websocket_stream() {
    let state = WebSocketState::new();
    let sim_id = "test_sim_e2e";

    // Step 1: Create broadcast channel (simulating simulation start)
    let sender = state.get_or_create_sender(sim_id).await;
    let mut rx = sender.subscribe();

    // Step 2: Simulate a running simulation sending 10Hz updates
    let updates_to_send = 10; // Simulate 1 second of updates

    for i in 0..updates_to_send {
        let update = SimulationUpdate {
            cars: (0..100)
                .map(|j| CarState {
                    id: j,
                    position: [32.5 + (i as f32 * 0.001), -117.0],
                    velocity: 10.0,
                    status: 1,
                    queue_id: Some(j % 3),
                    queue_position: Some(j),
                })
                .collect(),
            metrics: MetricsUpdate {
                total_arrivals: 100,
                total_completions: i as u32 * 10,
                average_wait_time: Some(60.0 + i as f64),
                simulation_time: i as f64 * 0.1,
            },
            service_nodes: vec![
                ServiceNodeState {
                    node_id: "booth_1".to_string(),
                    queue_id: 0,
                    is_busy: true,
                    current_car_id: Some(1),
                    service_rate: 3.0,
                    total_served: i as u32 * 5,
                },
            ],
            timestamp: i as f64 * 100.0,
        };

        let msg = ServerMessage::SimulationUpdate(update);
        let result = state.broadcast(sim_id, &msg).await;
        assert!(result.is_ok(), "Broadcast should succeed");
    }

    // Step 3: Receive and verify all updates
    let mut received = 0;
    let mut last_time = -1.0;

    while let Ok(result) = tokio::time::timeout(Duration::from_millis(100), rx.recv()).await {
        if let Ok(data) = result {
            let msg: ServerMessage = rmp_serde::from_slice(&data).unwrap();
            match msg {
                ServerMessage::SimulationUpdate(update) => {
                    // Verify updates are in order
                    assert!(
                        update.timestamp > last_time,
                        "Updates should be ordered: {} > {}",
                        update.timestamp,
                        last_time
                    );
                    last_time = update.timestamp;

                    // Verify data integrity
                    assert_eq!(update.cars.len(), 100);
                    assert!(update.metrics.simulation_time >= 0.0);

                    received += 1;
                }
                _ => panic!("Expected SimulationUpdate"),
            }
        }
    }

    assert_eq!(received, updates_to_send, "Should receive all {} updates", updates_to_send);

    // Step 4: Simulate stop - drop receiver
    drop(rx);

    // Verify no more subscribers
    assert_eq!(state.subscriber_count(sim_id).await, 0);

    println!("E2E WebSocket test passed: received {} updates in order", received);
}

/// Test WebSocket reconnection scenario
#[tokio::test]
async fn test_websocket_reconnection_scenario() {
    let state = WebSocketState::new();
    let sim_id = "reconnect_sim";

    // Initial connection
    let sender = state.get_or_create_sender(sim_id).await;
    let mut rx1 = sender.subscribe();

    // Send some updates
    for i in 0..5 {
        let msg = ServerMessage::Ack {
            message_id: Some(format!("msg_{}", i)),
        };
        let _ = state.broadcast(sim_id, &msg).await;
    }

    // Receive updates on first connection
    let mut count1 = 0;
    while let Ok(_) = tokio::time::timeout(Duration::from_millis(50), rx1.recv()).await {
        count1 += 1;
    }

    // Simulate disconnect
    drop(rx1);
    assert_eq!(state.subscriber_count(sim_id).await, 0);

    // Reconnect
    let mut rx2 = sender.subscribe();
    assert_eq!(state.subscriber_count(sim_id).await, 1);

    // After reconnect, client typically requests full state
    let full_state_request = ClientMessage::RequestFullState;
    let request_bytes = rmp_serde::to_vec(&full_state_request).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&request_bytes).unwrap();
    assert!(matches!(decoded, ClientMessage::RequestFullState));

    // Server sends full state after reconnect request
    let full_update = SimulationUpdate {
        cars: (0..50).map(|i| CarState {
            id: i,
            position: [32.5, -117.0],
            velocity: 10.0,
            status: 1,
            queue_id: Some(i % 3),
            queue_position: Some(i),
        }).collect(),
        metrics: MetricsUpdate {
            total_arrivals: 50,
            total_completions: 25,
            average_wait_time: Some(90.0),
            simulation_time: 300.0,
        },
        service_nodes: vec![],
        timestamp: 300.0,
    };

    let msg = ServerMessage::SimulationUpdate(full_update);
    let result = state.broadcast(sim_id, &msg).await;
    assert!(result.is_ok());

    // Verify reconnected client receives update
    let data = tokio::time::timeout(Duration::from_millis(100), rx2.recv())
        .await
        .expect("Should receive update")
        .expect("Channel should be open");

    let decoded: ServerMessage = rmp_serde::from_slice(&data).unwrap();
    match decoded {
        ServerMessage::SimulationUpdate(update) => {
            assert_eq!(update.cars.len(), 50);
            assert_eq!(update.metrics.simulation_time, 300.0);
        }
        _ => panic!("Expected SimulationUpdate after reconnect"),
    }

    println!("Reconnection test passed: client received {} updates before disconnect, received full state after reconnect", count1);
}

/// Test control message flow
#[tokio::test]
async fn test_control_message_flow() {
    // Test the full control message lifecycle

    // Pause command
    let pause = ClientMessage::Control(ControlMessage::Pause);
    let bytes = rmp_serde::to_vec(&pause).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
    assert!(matches!(decoded, ClientMessage::Control(ControlMessage::Pause)));

    // Resume command
    let resume = ClientMessage::Control(ControlMessage::Resume);
    let bytes = rmp_serde::to_vec(&resume).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
    assert!(matches!(decoded, ClientMessage::Control(ControlMessage::Resume)));

    // Time speed control
    let speed = ClientMessage::Control(ControlMessage::SetTimeSpeed { speed: 2.5 });
    let bytes = rmp_serde::to_vec(&speed).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ClientMessage::Control(ControlMessage::SetTimeSpeed { speed }) => {
            assert!((speed - 2.5).abs() < 0.01);
        }
        _ => panic!("Expected SetTimeSpeed"),
    }

    // Add station
    let add = ClientMessage::Control(ControlMessage::AddStation { queue_id: 0 });
    let bytes = rmp_serde::to_vec(&add).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ClientMessage::Control(ControlMessage::AddStation { queue_id }) => {
            assert_eq!(queue_id, 0);
        }
        _ => panic!("Expected AddStation"),
    }

    // Remove station
    let remove = ClientMessage::Control(ControlMessage::RemoveStation { node_id: "booth_1".to_string() });
    let bytes = rmp_serde::to_vec(&remove).unwrap();
    let decoded: ClientMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ClientMessage::Control(ControlMessage::RemoveStation { node_id }) => {
            assert_eq!(node_id, "booth_1");
        }
        _ => panic!("Expected RemoveStation"),
    }

    println!("All control messages serialized and deserialized correctly");
}

/// Test WebSocket with simulated high load (100 concurrent clients)
#[tokio::test]
async fn test_websocket_concurrent_clients() {
    let state = WebSocketState::new();
    let sim_id = "concurrent_test";

    // Create sender
    let sender = state.get_or_create_sender(sim_id).await;

    // Create 100 concurrent subscribers
    let num_clients = 100;
    let mut receivers: Vec<_> = (0..num_clients).map(|_| sender.subscribe()).collect();

    assert_eq!(state.subscriber_count(sim_id).await, num_clients);

    // Send a batch of updates
    let updates = 10;
    for i in 0..updates {
        let update = SimulationUpdate {
            cars: (0..1000).map(|j| CarState {
                id: j,
                position: [32.5 + (i as f32 * 0.001), -117.0 + (j as f32 * 0.0001)],
                velocity: 10.0,
                status: (j % 4) as u8,
                queue_id: Some(j % 5),
                queue_position: Some(j),
            }).collect(),
            metrics: MetricsUpdate {
                total_arrivals: 1000,
                total_completions: i as u32 * 100,
                average_wait_time: Some(120.0),
                simulation_time: i as f64 * 0.1,
            },
            service_nodes: vec![],
            timestamp: i as f64 * 100.0,
        };

        let msg = ServerMessage::SimulationUpdate(update);
        let result = state.broadcast(sim_id, &msg).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), num_clients as usize);
    }

    // Verify all clients received all updates
    let mut total_received = 0;
    for rx in &mut receivers {
        let mut client_received = 0;
        while let Ok(_) = tokio::time::timeout(Duration::from_millis(50), rx.recv()).await {
            client_received += 1;
        }
        total_received += client_received;
    }

    // Each client should receive all updates
    assert_eq!(total_received, num_clients * updates);

    println!("Concurrent clients test: {} clients each received {} updates", num_clients, updates);
}

/// Test error message handling
#[test]
fn test_error_message_types() {
    use cascabel_api::messages::ErrorMessage;

    // Connection error
    let conn_error = ServerMessage::Error(ErrorMessage {
        code: "1001".to_string(),
        message: "Connection closed unexpectedly".to_string(),
        details: Some("Connection timeout".to_string()),
    });
    let bytes = rmp_serde::to_vec(&conn_error).unwrap();
    let decoded: ServerMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ServerMessage::Error(err) => {
            assert_eq!(err.code, "1001");
            assert!(err.message.contains("Connection"));
            assert!(err.details.is_some());
        }
        _ => panic!("Expected Error"),
    }

    // Simulation not found error
    let not_found = ServerMessage::Error(ErrorMessage {
        code: "404".to_string(),
        message: "Simulation not found".to_string(),
        details: None,
    });
    let bytes = rmp_serde::to_vec(&not_found).unwrap();
    let decoded: ServerMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ServerMessage::Error(err) => {
            assert_eq!(err.code, "404");
            assert!(err.details.is_none());
        }
        _ => panic!("Expected Error"),
    }

    // Rate limit error
    let rate_limit = ServerMessage::Error(ErrorMessage {
        code: "429".to_string(),
        message: "Too many requests".to_string(),
        details: Some("Please retry after 60 seconds".to_string()),
    });
    let bytes = rmp_serde::to_vec(&rate_limit).unwrap();
    let decoded: ServerMessage = rmp_serde::from_slice(&bytes).unwrap();
    match decoded {
        ServerMessage::Error(err) => {
            assert_eq!(err.code, "429");
        }
        _ => panic!("Expected Error"),
    }

    println!("Error message handling test passed");
}
