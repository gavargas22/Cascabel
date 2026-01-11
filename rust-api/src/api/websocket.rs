//! WebSocket handler for real-time simulation streaming
//!
//! This module provides WebSocket endpoints for streaming simulation updates
//! to connected clients using MessagePack binary serialization.

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    response::IntoResponse,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};

use super::messages::{
    ClientMessage, ServerMessage, SimulationUpdate, PositionOnlyUpdate, MetricsUpdate,
    CarState, ServiceNodeState,
};

/// Shared state for WebSocket connection management
#[derive(Debug, Clone)]
pub struct WebSocketState {
    /// Map of simulation_id -> broadcast sender for that simulation
    pub senders: Arc<RwLock<HashMap<String, broadcast::Sender<Vec<u8>>>>>,
    /// Update rate in Hz (default: 10)
    pub update_rate_hz: u32,
    /// Whether to enable position-only updates at higher frequency
    pub enable_position_only_updates: bool,
    /// Position-only update rate in Hz (default: 30)
    pub position_only_rate_hz: u32,
}

impl WebSocketState {
    /// Create a new WebSocket state with default configuration
    pub fn new() -> Self {
        Self {
            senders: Arc::new(RwLock::new(HashMap::new())),
            update_rate_hz: 10,
            enable_position_only_updates: false,
            position_only_rate_hz: 30,
        }
    }

    /// Create with custom update rates
    pub fn with_update_rates(update_rate_hz: u32, position_only_rate_hz: u32) -> Self {
        Self {
            senders: Arc::new(RwLock::new(HashMap::new())),
            update_rate_hz,
            enable_position_only_updates: position_only_rate_hz > update_rate_hz,
            position_only_rate_hz,
        }
    }

    /// Get or create a broadcast channel for a simulation
    pub async fn get_or_create_sender(
        &self,
        simulation_id: &str,
    ) -> broadcast::Sender<Vec<u8>> {
        let mut senders = self.senders.write().await;
        if let Some(sender) = senders.get(simulation_id) {
            sender.clone()
        } else {
            // Create a new broadcast channel with capacity for 100 messages
            let (tx, _rx) = broadcast::channel(100);
            senders.insert(simulation_id.to_string(), tx.clone());
            tx
        }
    }

    /// Remove a simulation's broadcast channel
    pub async fn remove_sender(&self, simulation_id: &str) {
        let mut senders = self.senders.write().await;
        senders.remove(simulation_id);
    }

    /// Get subscriber count for a simulation
    pub async fn subscriber_count(&self, simulation_id: &str) -> usize {
        let senders = self.senders.read().await;
        if let Some(sender) = senders.get(simulation_id) {
            sender.receiver_count()
        } else {
            0
        }
    }

    /// Broadcast a message to all subscribers of a simulation
    pub async fn broadcast(
        &self,
        simulation_id: &str,
        message: &ServerMessage,
    ) -> Result<usize, BroadcastError> {
        let senders = self.senders.read().await;
        if let Some(sender) = senders.get(simulation_id) {
            let bytes = rmp_serde::to_vec(message)
                .map_err(|e| BroadcastError::SerializationError(e.to_string()))?;

            sender
                .send(bytes)
                .map_err(|_| BroadcastError::NoReceivers)
        } else {
            Err(BroadcastError::SimulationNotFound)
        }
    }
}

impl Default for WebSocketState {
    fn default() -> Self {
        Self::new()
    }
}

/// Errors that can occur during broadcast
#[derive(Debug, Clone, PartialEq)]
pub enum BroadcastError {
    SimulationNotFound,
    NoReceivers,
    SerializationError(String),
}

impl std::fmt::Display for BroadcastError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BroadcastError::SimulationNotFound => write!(f, "Simulation not found"),
            BroadcastError::NoReceivers => write!(f, "No receivers connected"),
            BroadcastError::SerializationError(e) => write!(f, "Serialization error: {}", e),
        }
    }
}

impl std::error::Error for BroadcastError {}

/// WebSocket upgrade handler for simulation streaming
///
/// This handler upgrades HTTP connections to WebSocket and starts streaming
/// simulation updates to the client.
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    Path(simulation_id): Path<String>,
    State(state): State<WebSocketState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, simulation_id, state))
}

/// Handle an individual WebSocket connection
async fn handle_socket(socket: WebSocket, simulation_id: String, state: WebSocketState) {
    use futures_util::{SinkExt, StreamExt};

    let (mut sender, mut receiver) = socket.split();

    // Get broadcast channel for this simulation
    let tx = state.get_or_create_sender(&simulation_id).await;
    let mut rx = tx.subscribe();

    // Spawn task to forward broadcast messages to this client
    let send_task = tokio::spawn(async move {
        while let Ok(msg) = rx.recv().await {
            if sender.send(Message::Binary(msg)).await.is_err() {
                break;
            }
        }
    });

    // Handle incoming messages from client
    let recv_task = tokio::spawn(async move {
        while let Some(result) = receiver.next().await {
            match result {
                Ok(Message::Binary(data)) => {
                    // Try to decode as ClientMessage
                    if let Ok(msg) = rmp_serde::from_slice::<ClientMessage>(&data) {
                        handle_client_message(msg).await;
                    }
                }
                Ok(Message::Text(text)) => {
                    // Also support JSON for debugging
                    if let Ok(msg) = serde_json::from_str::<ClientMessage>(&text) {
                        handle_client_message(msg).await;
                    }
                }
                Ok(Message::Ping(data)) => {
                    // Pong is handled automatically by axum
                    tracing::debug!("Received ping: {:?}", data);
                }
                Ok(Message::Pong(_)) => {
                    // Ignore pongs
                }
                Ok(Message::Close(_)) => {
                    break;
                }
                Err(e) => {
                    tracing::error!("WebSocket error: {}", e);
                    break;
                }
            }
        }
    });

    // Wait for either task to complete
    tokio::select! {
        _ = send_task => {},
        _ = recv_task => {},
    }

    tracing::info!("WebSocket connection closed for simulation {}", simulation_id);
}

/// Handle a message from the client
async fn handle_client_message(msg: ClientMessage) {
    match msg {
        ClientMessage::Control(control) => {
            tracing::info!("Received control message: {:?}", control);
            // Control messages will be handled by the simulation manager
        }
        ClientMessage::Heartbeat => {
            tracing::debug!("Received heartbeat");
        }
        ClientMessage::RequestFullState => {
            tracing::info!("Client requested full state");
        }
    }
}

/// Create a SimulationUpdate message from simulation state
pub fn create_simulation_update(
    cars: Vec<CarState>,
    metrics: MetricsUpdate,
    service_nodes: Vec<ServiceNodeState>,
) -> ServerMessage {
    ServerMessage::SimulationUpdate(SimulationUpdate {
        cars,
        metrics,
        service_nodes,
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64(),
    })
}

/// Create a PositionOnlyUpdate message for high-frequency updates
pub fn create_position_only_update(positions: Vec<(u32, f32, f32)>) -> ServerMessage {
    ServerMessage::PositionOnly(PositionOnlyUpdate {
        positions,
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== WebSocketState Tests ==========

    #[tokio::test]
    async fn test_websocket_state_creation() {
        let state = WebSocketState::new();
        assert_eq!(state.update_rate_hz, 10);
        assert!(!state.enable_position_only_updates);
        assert_eq!(state.position_only_rate_hz, 30);
    }

    #[tokio::test]
    async fn test_websocket_state_with_custom_rates() {
        let state = WebSocketState::with_update_rates(20, 60);
        assert_eq!(state.update_rate_hz, 20);
        assert!(state.enable_position_only_updates);
        assert_eq!(state.position_only_rate_hz, 60);
    }

    #[tokio::test]
    async fn test_get_or_create_sender() {
        let state = WebSocketState::new();

        // First call creates a new sender
        let sender1 = state.get_or_create_sender("sim1").await;
        assert_eq!(sender1.receiver_count(), 0);

        // Second call returns the same sender
        let sender2 = state.get_or_create_sender("sim1").await;
        assert_eq!(sender1.receiver_count(), sender2.receiver_count());
    }

    #[tokio::test]
    async fn test_remove_sender() {
        let state = WebSocketState::new();

        // Create a sender
        let _sender = state.get_or_create_sender("sim1").await;
        assert_eq!(state.subscriber_count("sim1").await, 0);

        // Remove it
        state.remove_sender("sim1").await;

        // Creating again should give a new sender
        let _sender2 = state.get_or_create_sender("sim1").await;
    }

    #[tokio::test]
    async fn test_subscriber_count() {
        let state = WebSocketState::new();

        // No subscribers initially
        assert_eq!(state.subscriber_count("sim1").await, 0);

        // Create sender and subscribe
        let sender = state.get_or_create_sender("sim1").await;
        let _rx = sender.subscribe();

        assert_eq!(state.subscriber_count("sim1").await, 1);
    }

    #[tokio::test]
    async fn test_broadcast_no_simulation() {
        let state = WebSocketState::new();

        let msg = ServerMessage::Heartbeat;
        let result = state.broadcast("nonexistent", &msg).await;

        assert_eq!(result, Err(BroadcastError::SimulationNotFound));
    }

    #[tokio::test]
    async fn test_broadcast_no_receivers() {
        let state = WebSocketState::new();

        // Create sender but no receivers
        let _sender = state.get_or_create_sender("sim1").await;

        let msg = ServerMessage::Heartbeat;
        let result = state.broadcast("sim1", &msg).await;

        assert_eq!(result, Err(BroadcastError::NoReceivers));
    }

    #[tokio::test]
    async fn test_broadcast_success() {
        let state = WebSocketState::new();

        // Create sender and subscribe
        let sender = state.get_or_create_sender("sim1").await;
        let mut rx = sender.subscribe();

        let msg = ServerMessage::Heartbeat;
        let result = state.broadcast("sim1", &msg).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 1); // 1 receiver

        // Verify message was received
        let received = rx.recv().await.unwrap();
        let decoded: ServerMessage = rmp_serde::from_slice(&received).unwrap();
        assert!(matches!(decoded, ServerMessage::Heartbeat));
    }

    // ========== Message Creation Tests ==========

    #[test]
    fn test_create_simulation_update() {
        let cars = vec![
            CarState {
                id: 1,
                position: [32.5, -117.0],
                velocity: 5.0,
                status: 1,
                queue_id: Some(0),
                queue_position: Some(1),
            },
        ];

        let metrics = MetricsUpdate {
            total_arrivals: 10,
            total_completions: 5,
            average_wait_time: Some(120.5),
            simulation_time: 300.0,
        };

        let service_nodes = vec![
            ServiceNodeState {
                node_id: "booth_1".to_string(),
                queue_id: 0,
                is_busy: true,
                current_car_id: Some(1),
                service_rate: 3.0,
                total_served: 5,
            },
        ];

        let msg = create_simulation_update(cars.clone(), metrics.clone(), service_nodes.clone());

        match msg {
            ServerMessage::SimulationUpdate(update) => {
                assert_eq!(update.cars.len(), 1);
                assert_eq!(update.cars[0].id, 1);
                assert_eq!(update.metrics.total_arrivals, 10);
                assert_eq!(update.service_nodes.len(), 1);
                assert!(update.timestamp > 0.0);
            }
            _ => panic!("Expected SimulationUpdate"),
        }
    }

    #[test]
    fn test_create_position_only_update() {
        let positions = vec![
            (1, 32.5_f32, -117.0_f32),
            (2, 32.6_f32, -117.1_f32),
        ];

        let msg = create_position_only_update(positions);

        match msg {
            ServerMessage::PositionOnly(update) => {
                assert_eq!(update.positions.len(), 2);
                assert_eq!(update.positions[0].0, 1);
                assert!(update.timestamp > 0.0);
            }
            _ => panic!("Expected PositionOnly"),
        }
    }

    // ========== Error Display Tests ==========

    #[test]
    fn test_broadcast_error_display() {
        assert_eq!(
            BroadcastError::SimulationNotFound.to_string(),
            "Simulation not found"
        );
        assert_eq!(
            BroadcastError::NoReceivers.to_string(),
            "No receivers connected"
        );
        assert_eq!(
            BroadcastError::SerializationError("test".to_string()).to_string(),
            "Serialization error: test"
        );
    }
}
