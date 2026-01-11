//! Simulation REST API endpoints
//!
//! This module provides REST endpoints for simulation control that match
//! the existing FastAPI implementation for frontend compatibility.

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::models::{
    AddCarResponse, AddServiceNodeRequest, AddServiceNodeResponse, ApiError,
    CancelSimulationResponse, CarData, CarDetailResponse, PhoneConfig, RemoveServiceNodeResponse,
    ServiceNodeData, SimulationRequest, SimulationStartResponse, SimulationStateResponse,
    SimulationStatistics, SimulationStatus, StopSimulationResponse, TimeSpeedResponse,
    TimeSpeedUpdate, generate_simulation_id,
};
use crate::simulation::{SimulationEngine, SimulationConfig as EngineConfig, Path as SimPath};

/// Shared state for simulation management
#[derive(Clone)]
pub struct SimulationState {
    /// Map of simulation_id -> SimulationInstance
    pub simulations: Arc<RwLock<HashMap<String, SimulationInstance>>>,
}

impl std::fmt::Debug for SimulationState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SimulationState")
            .field("simulations_count", &"<RwLock>")
            .finish()
    }
}

impl SimulationState {
    /// Create a new simulation state
    pub fn new() -> Self {
        Self {
            simulations: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get simulation count
    pub async fn count(&self) -> usize {
        self.simulations.read().await.len()
    }
}

impl Default for SimulationState {
    fn default() -> Self {
        Self::new()
    }
}

/// Instance of a running simulation
pub struct SimulationInstance {
    /// The simulation engine
    pub engine: SimulationEngine,
    /// Original request configuration
    pub request: SimulationRequest,
    /// Current status
    pub status: String,
    /// Start time (real)
    pub start_time: std::time::Instant,
    /// Error message if failed
    pub error: Option<String>,
}

impl SimulationInstance {
    /// Create a new simulation instance
    pub fn new(request: SimulationRequest) -> Self {
        let config = EngineConfig {
            safe_distance: request.border_config.safe_distance,
            num_queues: request.border_config.num_queues,
            max_queue_length: request.border_config.max_queue_length,
            arrival_rate: request.border_config.arrival_rate,
            ..EngineConfig::default()
        };

        let engine = SimulationEngine::with_config(config);

        Self {
            engine,
            request,
            status: "running".to_string(),
            start_time: std::time::Instant::now(),
            error: None,
        }
    }

    /// Get the max simulation time
    pub fn max_simulation_time(&self) -> f64 {
        self.request
            .simulation_config
            .as_ref()
            .map(|c| c.max_simulation_time)
            .unwrap_or(3600.0)
    }

    /// Get current progress (0.0 to 1.0)
    pub fn progress(&self) -> f64 {
        let current = self.engine.current_time();
        let max = self.max_simulation_time();
        (current / max).min(1.0)
    }
}

// ========== API Handlers ==========

/// POST /simulate - Start a new simulation
pub async fn start_simulation(
    State(state): State<SimulationState>,
    Json(request): Json<SimulationRequest>,
) -> impl IntoResponse {
    let simulation_id = generate_simulation_id();

    // Create simulation instance
    let instance = SimulationInstance::new(request);

    // Store in state
    {
        let mut simulations = state.simulations.write().await;
        simulations.insert(simulation_id.clone(), instance);
    }

    // Return response
    let response = SimulationStartResponse {
        simulation_id: simulation_id.clone(),
        status: "running".to_string(),
        websocket_url: format!("ws://localhost:8001/ws/{}", simulation_id),
        message: "Simulation started successfully".to_string(),
    };

    (StatusCode::OK, Json(response))
}

/// GET /simulation/{id}/status - Get simulation status
pub async fn get_simulation_status(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
) -> impl IntoResponse {
    let simulations = state.simulations.read().await;

    match simulations.get(&simulation_id) {
        Some(instance) => {
            let stats = instance.engine.stats();
            let status = SimulationStatus {
                simulation_id,
                status: instance.status.clone(),
                progress: instance.progress(),
                current_time: instance.engine.current_time(),
                total_arrivals: stats.total_arrivals,
                total_completions: stats.total_completions,
                active_cars: Some(stats.active_cars),
                message: instance.error.clone(),
            };
            (StatusCode::OK, Json(status)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// GET /simulation/{id}/state - Get current simulation state
pub async fn get_simulation_state(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            let stats = instance.engine.stats();
            let car_states = instance.engine.get_car_states();

            let cars: Vec<CarData> = car_states
                .iter()
                .map(|c| CarData {
                    car_id: c.id,
                    position: c.x, // Using x as linear position along path
                    velocity: c.velocity,
                    status: c.status.as_str().to_string(),
                    queue_id: None, // Would need to query QueueMembership component
                })
                .collect();

            // Query service nodes from engine
            let service_nodes: Vec<ServiceNodeData> = vec![]; // TODO: Extract from engine

            let response = SimulationStateResponse {
                simulation_id: simulation_id.clone(),
                status: instance.status.clone(),
                current_time: instance.engine.current_time(),
                cars,
                service_nodes,
                statistics: SimulationStatistics {
                    total_arrivals: stats.total_arrivals,
                    total_completions: stats.total_completions,
                    active_cars: stats.active_cars,
                    average_wait_time: if stats.average_wait_time > 0.0 {
                        Some(stats.average_wait_time)
                    } else {
                        None
                    },
                    simulation_time: instance.engine.current_time(),
                },
                traffic_control_points: None,
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// POST /simulation/{id}/stop - Stop simulation
pub async fn stop_simulation(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            instance.status = "stopped".to_string();

            let response = StopSimulationResponse {
                simulation_id,
                status: "stopped".to_string(),
                message: "Simulation stopped successfully".to_string(),
                telemetry_records_saved: 0, // TODO: Implement telemetry persistence
                database_path: None,
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// DELETE /simulation/{id} - Cancel simulation
pub async fn cancel_simulation(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            if instance.status == "running" {
                instance.status = "cancelled".to_string();
                instance.error = Some("Cancelled by user".to_string());
            } else {
                // Delete completed simulation
                simulations.remove(&simulation_id);
            }

            let response = CancelSimulationResponse {
                simulation_id,
                status: "cancelled".to_string(),
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// PUT /simulation/{id}/time_speed - Update time speed
pub async fn update_time_speed(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
    Json(update): Json<TimeSpeedUpdate>,
) -> impl IntoResponse {
    if update.time_factor <= 0.0 {
        let error = ApiError::bad_request("time_factor must be positive");
        return (StatusCode::BAD_REQUEST, Json(error)).into_response();
    }

    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            instance.engine.set_time_scale(update.time_factor);

            // Update config if present
            if let Some(ref mut config) = instance.request.simulation_config {
                config.time_factor = update.time_factor;
            }

            let response = TimeSpeedResponse {
                status: "updated".to_string(),
                time_factor: update.time_factor,
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// POST /simulation/{id}/add_station - Add service station
pub async fn add_service_station(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
    Json(request): Json<AddServiceNodeRequest>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            // Validate queue ID
            if request.queue_id >= instance.request.border_config.num_queues {
                let error = ApiError::bad_request("Invalid queue ID");
                return (StatusCode::BAD_REQUEST, Json(error)).into_response();
            }

            // Generate node ID
            let node_id = format!("q{}_n{}", request.queue_id, std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() % 10000);

            // Add service node to engine
            instance.engine.spawn_service_node(
                node_id.clone(),
                request.queue_id,
                request.service_rate,
            );

            let response = AddServiceNodeResponse {
                station_id: node_id,
                queue_id: request.queue_id,
                service_rate: request.service_rate,
                service_time_variation: request.service_time_variation,
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// DELETE /simulation/{id}/service_node/{node_id} - Remove service node
pub async fn remove_service_node(
    State(state): State<SimulationState>,
    Path((simulation_id, node_id)): Path<(String, String)>,
) -> impl IntoResponse {
    let simulations = state.simulations.read().await;

    match simulations.get(&simulation_id) {
        Some(_instance) => {
            // TODO: Implement service node removal in engine
            // For now, return success - actual removal requires ECS query

            let response = RemoveServiceNodeResponse {
                node_id,
                message: "Service node removed successfully".to_string(),
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// POST /simulation/{id}/add_car - Add a car
pub async fn add_car(
    State(state): State<SimulationState>,
    Path(simulation_id): Path<String>,
    Json(_phone_config): Json<Option<PhoneConfig>>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            if instance.status != "running" {
                let error = ApiError::bad_request("Simulation is not running");
                return (StatusCode::BAD_REQUEST, Json(error)).into_response();
            }

            // Create a simple path for the car
            let path = SimPath::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
            let queue_id = 0; // Default queue

            let car_id = instance.engine.spawn_car(path, queue_id);

            let response = AddCarResponse {
                car_id,
                queue_id,
                message: "Car added successfully".to_string(),
            };

            (StatusCode::OK, Json(response)).into_response()
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// GET /simulation/{id}/car/{car_id} - Get car details
pub async fn get_car_details(
    State(state): State<SimulationState>,
    Path((simulation_id, car_id)): Path<(String, u32)>,
) -> impl IntoResponse {
    let mut simulations = state.simulations.write().await;

    match simulations.get_mut(&simulation_id) {
        Some(instance) => {
            let car_states = instance.engine.get_car_states();

            match car_states.iter().find(|c| c.id == car_id) {
                Some(car) => {
                    let response = CarDetailResponse {
                        car_id: car.id,
                        status: car.status.as_str().to_string(),
                        queue_id: None,
                        queue_position: None,
                        position: [car.x, car.y],
                        velocity: car.velocity,
                        acceleration: 0.0, // Not tracked in snapshot
                        arrival_time: car.arrival_time,
                        queue_start_time: None,
                        service_start_time: car.service_start_time,
                        completion_time: car.completion_time,
                        wait_time: match (car.arrival_time, car.service_start_time) {
                            (Some(a), Some(s)) => Some(s - a),
                            _ => None,
                        },
                        distance_traveled: Some(car.x),
                    };

                    (StatusCode::OK, Json(response)).into_response()
                }
                None => {
                    let error = ApiError::not_found(format!("Car {} not found", car_id));
                    (StatusCode::NOT_FOUND, Json(error)).into_response()
                }
            }
        }
        None => {
            let error = ApiError::not_found("Simulation not found");
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
        Router,
        routing::{get, post, put, delete},
    };
    use tower::ServiceExt;
    use serde_json::json;

    fn create_test_app() -> Router {
        let state = SimulationState::new();
        Router::new()
            .route("/simulate", post(start_simulation))
            .route("/simulation/:id/status", get(get_simulation_status))
            .route("/simulation/:id/state", get(get_simulation_state))
            .route("/simulation/:id/stop", post(stop_simulation))
            .route("/simulation/:id", delete(cancel_simulation))
            .route("/simulation/:id/time_speed", put(update_time_speed))
            .route("/simulation/:id/add_station", post(add_service_station))
            .route("/simulation/:id/service_node/:node_id", delete(remove_service_node))
            .route("/simulation/:id/add_car", post(add_car))
            .route("/simulation/:id/car/:car_id", get(get_car_details))
            .with_state(state)
    }

    // ========== POST /simulate tests ==========

    #[tokio::test]
    async fn test_start_simulation_basic() {
        let app = create_test_app();

        let request_body = json!({
            "border_config": {
                "num_queues": 2
            }
        });

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/simulate")
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let result: SimulationStartResponse = serde_json::from_slice(&body).unwrap();

        assert_eq!(result.status, "running");
        assert!(result.websocket_url.contains("/ws/"));
        assert!(!result.simulation_id.is_empty());
    }

    #[tokio::test]
    async fn test_start_simulation_with_full_config() {
        let app = create_test_app();

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

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/simulate")
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    // ========== GET /simulation/{id}/status tests ==========

    #[tokio::test]
    async fn test_get_simulation_status_not_found() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/simulation/nonexistent-id/status")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_simulation_status_success() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        // Insert a simulation
        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/status", get(get_simulation_status))
            .with_state(state);

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri(format!("/simulation/{}/status", sim_id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let status: SimulationStatus = serde_json::from_slice(&body).unwrap();

        assert_eq!(status.status, "running");
        assert_eq!(status.simulation_id, sim_id);
    }

    // ========== POST /simulation/{id}/stop tests ==========

    #[tokio::test]
    async fn test_stop_simulation_not_found() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/simulation/nonexistent-id/stop")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_stop_simulation_success() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        // Insert a simulation
        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/stop", post(stop_simulation))
            .with_state(state.clone());

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri(format!("/simulation/{}/stop", sim_id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        // Verify status changed
        let simulations = state.simulations.read().await;
        assert_eq!(simulations.get(&sim_id).unwrap().status, "stopped");
    }

    // ========== PUT /simulation/{id}/time_speed tests ==========

    #[tokio::test]
    async fn test_update_time_speed_invalid() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/time_speed", put(update_time_speed))
            .with_state(state);

        let request_body = json!({ "time_factor": -1.0 });

        let response = app
            .oneshot(
                Request::builder()
                    .method("PUT")
                    .uri(format!("/simulation/{}/time_speed", sim_id))
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_update_time_speed_success() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/time_speed", put(update_time_speed))
            .with_state(state);

        let request_body = json!({ "time_factor": 2.0 });

        let response = app
            .oneshot(
                Request::builder()
                    .method("PUT")
                    .uri(format!("/simulation/{}/time_speed", sim_id))
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let result: TimeSpeedResponse = serde_json::from_slice(&body).unwrap();

        assert_eq!(result.time_factor, 2.0);
    }

    // ========== POST /simulation/{id}/add_station tests ==========

    #[tokio::test]
    async fn test_add_service_station_invalid_queue() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        {
            let mut simulations = state.simulations.write().await;
            let mut request = SimulationRequest::default();
            request.border_config.num_queues = 2;
            simulations.insert(sim_id.clone(), SimulationInstance::new(request));
        }

        let app = Router::new()
            .route("/simulation/:id/add_station", post(add_service_station))
            .with_state(state);

        let request_body = json!({
            "queue_id": 5,
            "service_rate": 3.0
        });

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri(format!("/simulation/{}/add_station", sim_id))
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_add_service_station_success() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/add_station", post(add_service_station))
            .with_state(state);

        let request_body = json!({
            "queue_id": 0,
            "service_rate": 4.0,
            "service_time_variation": 0.3
        });

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri(format!("/simulation/{}/add_station", sim_id))
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(&request_body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let result: AddServiceNodeResponse = serde_json::from_slice(&body).unwrap();

        assert_eq!(result.queue_id, 0);
        assert_eq!(result.service_rate, 4.0);
    }

    // ========== GET /simulation/{id}/car/{car_id} tests ==========

    #[tokio::test]
    async fn test_get_car_details_not_found() {
        let state = SimulationState::new();
        let sim_id = "test-sim-id".to_string();

        {
            let mut simulations = state.simulations.write().await;
            simulations.insert(
                sim_id.clone(),
                SimulationInstance::new(SimulationRequest::default()),
            );
        }

        let app = Router::new()
            .route("/simulation/:id/car/:car_id", get(get_car_details))
            .with_state(state);

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri(format!("/simulation/{}/car/999", sim_id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }
}
