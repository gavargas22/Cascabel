//! WebSocket message types with MessagePack serialization
//!
//! This module defines all message types used for WebSocket communication
//! between the Rust backend and frontend clients. Messages are serialized
//! using MessagePack for efficient binary transmission (~50% smaller than JSON).

use serde::{Deserialize, Serialize};

/// Server-to-client message types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMessage {
    /// Full simulation state update (sent at 10Hz)
    SimulationUpdate(SimulationUpdate),
    /// Position-only update for high-frequency streaming (sent at 30Hz)
    PositionOnly(PositionOnlyUpdate),
    /// Metrics-only update
    Metrics(MetricsUpdate),
    /// Error message
    Error(ErrorMessage),
    /// Heartbeat response
    Heartbeat,
    /// Acknowledgment of control message
    Ack { message_id: Option<String> },
}

/// Client-to-server message types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMessage {
    /// Control message (pause, resume, speed change)
    Control(ControlMessage),
    /// Heartbeat ping
    Heartbeat,
    /// Request full state (e.g., after reconnection)
    RequestFullState,
}

/// Full simulation update containing all car states and metrics
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SimulationUpdate {
    /// Current state of all cars
    pub cars: Vec<CarState>,
    /// Current metrics
    pub metrics: MetricsUpdate,
    /// Service node states
    pub service_nodes: Vec<ServiceNodeState>,
    /// Timestamp in seconds since epoch
    pub timestamp: f64,
}

/// Compact position-only update for high-frequency streaming
/// Each position is (car_id, lat, lon) using f32 for size efficiency
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PositionOnlyUpdate {
    /// Position tuples: (car_id, latitude, longitude)
    pub positions: Vec<(u32, f32, f32)>,
    /// Timestamp in seconds since epoch
    pub timestamp: f64,
}

/// Metrics update message
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MetricsUpdate {
    /// Total number of car arrivals
    pub total_arrivals: u32,
    /// Total number of completed services
    pub total_completions: u32,
    /// Average wait time in seconds (None if no data)
    pub average_wait_time: Option<f64>,
    /// Current simulation time in seconds
    pub simulation_time: f64,
}

/// Individual car state for full updates
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CarState {
    /// Unique car ID
    pub id: u32,
    /// GPS position as [latitude, longitude] using f32 for size
    pub position: [f32; 2],
    /// Current velocity in m/s (f32 for size)
    pub velocity: f32,
    /// Status code: 0=approaching, 1=queued, 2=serving, 3=completed
    pub status: u8,
    /// Queue ID (if assigned)
    pub queue_id: Option<u32>,
    /// Position in queue (1=front)
    pub queue_position: Option<u32>,
}

impl CarState {
    /// Size in bytes for MessagePack serialization (approximate)
    /// id(4) + position(8) + velocity(4) + status(1) = 17 bytes minimum
    pub const MIN_BYTES: usize = 17;

    /// Convert status code to string
    pub fn status_str(&self) -> &'static str {
        match self.status {
            0 => "approaching",
            1 => "queued",
            2 => "serving",
            3 => "completed",
            _ => "unknown",
        }
    }
}

/// Service node state
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ServiceNodeState {
    /// Node identifier
    pub node_id: String,
    /// Queue this node belongs to
    pub queue_id: u32,
    /// Whether the node is currently serving
    pub is_busy: bool,
    /// ID of car being served (if any)
    pub current_car_id: Option<u32>,
    /// Service rate (cars per minute)
    pub service_rate: f64,
    /// Total cars served
    pub total_served: u32,
}

/// Control message from client
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "action", rename_all = "snake_case")]
pub enum ControlMessage {
    /// Pause the simulation
    Pause,
    /// Resume the simulation
    Resume,
    /// Change simulation time speed
    SetTimeSpeed { speed: f64 },
    /// Request to add a service station
    AddStation { queue_id: u32 },
    /// Request to remove a service station
    RemoveStation { node_id: String },
}

/// Error message from server
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ErrorMessage {
    /// Error code
    pub code: String,
    /// Human-readable error message
    pub message: String,
    /// Additional details
    pub details: Option<String>,
}

impl ErrorMessage {
    /// Create a new error message
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
            details: None,
        }
    }

    /// Add details to the error
    pub fn with_details(mut self, details: impl Into<String>) -> Self {
        self.details = Some(details.into());
        self
    }
}

/// Helper to serialize a message to MessagePack bytes
pub fn serialize_to_msgpack<T: Serialize>(msg: &T) -> Result<Vec<u8>, rmp_serde::encode::Error> {
    rmp_serde::to_vec(msg)
}

/// Helper to deserialize a message from MessagePack bytes
pub fn deserialize_from_msgpack<'a, T: Deserialize<'a>>(
    bytes: &'a [u8],
) -> Result<T, rmp_serde::decode::Error> {
    rmp_serde::from_slice(bytes)
}

/// Helper to serialize a message to JSON string
pub fn serialize_to_json<T: Serialize>(msg: &T) -> Result<String, serde_json::Error> {
    serde_json::to_string(msg)
}

/// Helper to deserialize a message from JSON string
pub fn deserialize_from_json<'a, T: Deserialize<'a>>(
    json: &'a str,
) -> Result<T, serde_json::Error> {
    serde_json::from_str(json)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== CarState Tests ==========

    #[test]
    fn test_car_state_creation() {
        let car = CarState {
            id: 1,
            position: [32.5, -117.0],
            velocity: 5.5,
            status: 1,
            queue_id: Some(0),
            queue_position: Some(1),
        };

        assert_eq!(car.id, 1);
        assert_eq!(car.status_str(), "queued");
    }

    #[test]
    fn test_car_state_status_strings() {
        assert_eq!(CarState { id: 0, position: [0.0, 0.0], velocity: 0.0, status: 0, queue_id: None, queue_position: None }.status_str(), "approaching");
        assert_eq!(CarState { id: 0, position: [0.0, 0.0], velocity: 0.0, status: 1, queue_id: None, queue_position: None }.status_str(), "queued");
        assert_eq!(CarState { id: 0, position: [0.0, 0.0], velocity: 0.0, status: 2, queue_id: None, queue_position: None }.status_str(), "serving");
        assert_eq!(CarState { id: 0, position: [0.0, 0.0], velocity: 0.0, status: 3, queue_id: None, queue_position: None }.status_str(), "completed");
        assert_eq!(CarState { id: 0, position: [0.0, 0.0], velocity: 0.0, status: 99, queue_id: None, queue_position: None }.status_str(), "unknown");
    }

    // ========== MessagePack Serialization Tests ==========

    #[test]
    fn test_car_state_msgpack_serialization() {
        let car = CarState {
            id: 1,
            position: [32.5, -117.0],
            velocity: 5.5,
            status: 1,
            queue_id: Some(0),
            queue_position: Some(1),
        };

        let bytes = serialize_to_msgpack(&car).unwrap();
        let decoded: CarState = deserialize_from_msgpack(&bytes).unwrap();

        assert_eq!(car, decoded);
    }

    #[test]
    fn test_simulation_update_msgpack_serialization() {
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
            service_nodes: vec![
                ServiceNodeState {
                    node_id: "booth_1".to_string(),
                    queue_id: 0,
                    is_busy: true,
                    current_car_id: Some(1),
                    service_rate: 3.0,
                    total_served: 50,
                },
            ],
            timestamp: 1234567890.123,
        };

        let bytes = serialize_to_msgpack(&update).unwrap();
        let decoded: SimulationUpdate = deserialize_from_msgpack(&bytes).unwrap();

        assert_eq!(update, decoded);
    }

    #[test]
    fn test_server_message_msgpack_serialization() {
        // Test SimulationUpdate variant
        let msg = ServerMessage::SimulationUpdate(SimulationUpdate {
            cars: vec![],
            metrics: MetricsUpdate {
                total_arrivals: 0,
                total_completions: 0,
                average_wait_time: None,
                simulation_time: 0.0,
            },
            service_nodes: vec![],
            timestamp: 0.0,
        });

        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ServerMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);

        // Test Heartbeat variant
        let msg = ServerMessage::Heartbeat;
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ServerMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);

        // Test Error variant
        let msg = ServerMessage::Error(ErrorMessage::new("TEST_ERROR", "Test message"));
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ServerMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);
    }

    #[test]
    fn test_client_message_msgpack_serialization() {
        // Test Control variant
        let msg = ClientMessage::Control(ControlMessage::Pause);
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ClientMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);

        // Test SetTimeSpeed
        let msg = ClientMessage::Control(ControlMessage::SetTimeSpeed { speed: 2.0 });
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ClientMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);

        // Test Heartbeat
        let msg = ClientMessage::Heartbeat;
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ClientMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);

        // Test RequestFullState
        let msg = ClientMessage::RequestFullState;
        let bytes = serialize_to_msgpack(&msg).unwrap();
        let decoded: ClientMessage = deserialize_from_msgpack(&bytes).unwrap();
        assert_eq!(msg, decoded);
    }

    #[test]
    fn test_position_only_update_msgpack_serialization() {
        let update = PositionOnlyUpdate {
            positions: vec![
                (1, 32.5_f32, -117.0_f32),
                (2, 32.6_f32, -117.1_f32),
                (3, 32.7_f32, -117.2_f32),
            ],
            timestamp: 1234567890.123,
        };

        let bytes = serialize_to_msgpack(&update).unwrap();
        let decoded: PositionOnlyUpdate = deserialize_from_msgpack(&bytes).unwrap();

        assert_eq!(update, decoded);
    }

    // ========== Size Comparison Tests (MessagePack vs JSON) ==========

    #[test]
    fn test_msgpack_smaller_than_json_single_car() {
        let car = CarState {
            id: 12345,
            position: [32.534567, -117.123456],
            velocity: 13.4112,
            status: 1,
            queue_id: Some(0),
            queue_position: Some(5),
        };

        let msgpack_bytes = serialize_to_msgpack(&car).unwrap();
        let json_string = serialize_to_json(&car).unwrap();

        println!(
            "Single car - MessagePack: {} bytes, JSON: {} bytes",
            msgpack_bytes.len(),
            json_string.len()
        );

        // MessagePack should be significantly smaller
        assert!(
            msgpack_bytes.len() < json_string.len(),
            "MessagePack ({}) should be smaller than JSON ({})",
            msgpack_bytes.len(),
            json_string.len()
        );
    }

    #[test]
    fn test_msgpack_smaller_than_json_many_cars() {
        let cars: Vec<CarState> = (0..100)
            .map(|i| CarState {
                id: i,
                position: [32.5 + (i as f32 * 0.001), -117.0 + (i as f32 * 0.001)],
                velocity: 10.0 + (i as f32 * 0.1),
                status: (i % 4) as u8,
                queue_id: if i % 2 == 0 { Some(0) } else { None },
                queue_position: if i % 2 == 0 { Some(i) } else { None },
            })
            .collect();

        let msgpack_bytes = serialize_to_msgpack(&cars).unwrap();
        let json_string = serialize_to_json(&cars).unwrap();

        println!(
            "100 cars - MessagePack: {} bytes, JSON: {} bytes",
            msgpack_bytes.len(),
            json_string.len()
        );

        let ratio = msgpack_bytes.len() as f64 / json_string.len() as f64;
        println!("MessagePack is {:.1}% of JSON size", ratio * 100.0);

        // MessagePack should be at least 40% smaller
        assert!(
            ratio < 0.6,
            "MessagePack should be less than 60% of JSON size, but is {:.1}%",
            ratio * 100.0
        );
    }

    #[test]
    fn test_msgpack_smaller_than_json_full_update() {
        let update = SimulationUpdate {
            cars: (0..5000)
                .map(|i| CarState {
                    id: i,
                    position: [32.5 + (i as f32 * 0.0001), -117.0 + (i as f32 * 0.0001)],
                    velocity: 10.0 + (i as f32 * 0.01),
                    status: (i % 4) as u8,
                    queue_id: if i % 2 == 0 { Some(i % 3) } else { None },
                    queue_position: if i % 2 == 0 { Some(i) } else { None },
                })
                .collect(),
            metrics: MetricsUpdate {
                total_arrivals: 5000,
                total_completions: 2500,
                average_wait_time: Some(180.5),
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
            timestamp: 1234567890.123,
        };

        let msgpack_bytes = serialize_to_msgpack(&update).unwrap();
        let json_string = serialize_to_json(&update).unwrap();

        println!(
            "5000 cars full update - MessagePack: {} bytes ({:.2} KB), JSON: {} bytes ({:.2} KB)",
            msgpack_bytes.len(),
            msgpack_bytes.len() as f64 / 1024.0,
            json_string.len(),
            json_string.len() as f64 / 1024.0
        );

        let ratio = msgpack_bytes.len() as f64 / json_string.len() as f64;
        println!(
            "MessagePack is {:.1}% of JSON size (~{:.0}% smaller)",
            ratio * 100.0,
            (1.0 - ratio) * 100.0
        );

        // Verify at least ~50% size reduction
        assert!(
            ratio < 0.55,
            "MessagePack should be less than 55% of JSON size for full update, but is {:.1}%",
            ratio * 100.0
        );
    }

    #[test]
    fn test_position_only_much_smaller() {
        let positions: Vec<(u32, f32, f32)> = (0..5000)
            .map(|i| (i, 32.5 + (i as f32 * 0.0001), -117.0 + (i as f32 * 0.0001)))
            .collect();

        let position_update = PositionOnlyUpdate {
            positions: positions.clone(),
            timestamp: 1234567890.123,
        };

        // Compare with full car states
        let full_update: Vec<CarState> = positions
            .iter()
            .map(|(id, lat, lon)| CarState {
                id: *id,
                position: [*lat, *lon],
                velocity: 10.0,
                status: 1,
                queue_id: Some(0),
                queue_position: Some(*id),
            })
            .collect();

        let position_bytes = serialize_to_msgpack(&position_update).unwrap();
        let full_bytes = serialize_to_msgpack(&full_update).unwrap();

        println!(
            "5000 positions - Position-only: {} bytes ({:.2} KB), Full: {} bytes ({:.2} KB)",
            position_bytes.len(),
            position_bytes.len() as f64 / 1024.0,
            full_bytes.len(),
            full_bytes.len() as f64 / 1024.0
        );

        let ratio = position_bytes.len() as f64 / full_bytes.len() as f64;
        println!(
            "Position-only is {:.1}% of full update size",
            ratio * 100.0
        );

        // Position-only should be much smaller than full update
        assert!(
            ratio < 0.7,
            "Position-only should be less than 70% of full update size"
        );
    }

    // ========== JSON Serialization Tests (for debugging) ==========

    #[test]
    fn test_json_serialization() {
        let msg = ServerMessage::SimulationUpdate(SimulationUpdate {
            cars: vec![CarState {
                id: 1,
                position: [32.5, -117.0],
                velocity: 5.5,
                status: 1,
                queue_id: Some(0),
                queue_position: Some(1),
            }],
            metrics: MetricsUpdate {
                total_arrivals: 10,
                total_completions: 5,
                average_wait_time: Some(120.5),
                simulation_time: 300.0,
            },
            service_nodes: vec![],
            timestamp: 1234567890.123,
        });

        let json = serialize_to_json(&msg).unwrap();
        let decoded: ServerMessage = deserialize_from_json(&json).unwrap();

        assert_eq!(msg, decoded);

        // Verify JSON structure
        assert!(json.contains("\"type\":\"simulation_update\""));
        assert!(json.contains("\"cars\""));
        assert!(json.contains("\"metrics\""));
    }

    #[test]
    fn test_control_message_json() {
        let msg = ClientMessage::Control(ControlMessage::SetTimeSpeed { speed: 2.0 });
        let json = serialize_to_json(&msg).unwrap();

        assert!(json.contains("\"type\":\"control\""));
        assert!(json.contains("\"action\":\"set_time_speed\""));
        assert!(json.contains("\"speed\":2.0"));
    }

    // ========== Error Message Tests ==========

    #[test]
    fn test_error_message_creation() {
        let error = ErrorMessage::new("SIMULATION_NOT_FOUND", "Simulation does not exist");
        assert_eq!(error.code, "SIMULATION_NOT_FOUND");
        assert_eq!(error.message, "Simulation does not exist");
        assert!(error.details.is_none());

        let error_with_details =
            ErrorMessage::new("INVALID_REQUEST", "Bad request").with_details("Missing field: id");
        assert_eq!(error_with_details.details, Some("Missing field: id".to_string()));
    }
}
