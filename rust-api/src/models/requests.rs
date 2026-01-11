//! Request and Response types for REST API endpoints
//!
//! These types match the frontend TypeScript types and Python Pydantic models
//! for API compatibility.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::config::{
    BorderCrossingConfig, PhoneConfig, PhysicsConfig, PhysicsRanges, SimulationConfig,
};

/// Request to start a new simulation
/// Matches Python SimulationRequest and TypeScript SimulationRequest
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationRequest {
    /// Border crossing configuration
    pub border_config: BorderCrossingConfig,
    /// Simulation configuration (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub simulation_config: Option<SimulationConfig>,
    /// Phone/device configuration (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phone_config: Option<PhoneConfig>,
    /// Physics configuration (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub physics_config: Option<PhysicsConfig>,
    /// Physics ranges for random selection (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub physics_ranges: Option<PhysicsRanges>,
    /// Name of border crossing (e.g., "paso_del_norte")
    #[serde(default = "default_crossing_name")]
    pub crossing_name: String,
    /// Traffic direction: "mx2usa" or "usa2mx"
    #[serde(default = "default_direction")]
    pub direction: String,
    /// Visual queue spacing (meters) - deprecated, use physics_ranges
    #[serde(default = "default_queue_spacing")]
    pub queue_spacing: f64,
    /// GeoJSON path (legacy support)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub geojson_path: Option<String>,
    /// Whether to use dynamic paths
    #[serde(default = "default_true")]
    pub use_dynamic_paths: bool,
    /// Country of origin (deprecated)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub country_of_origin: Option<String>,
}

fn default_crossing_name() -> String { "paso_del_norte".to_string() }
fn default_direction() -> String { "mx2usa".to_string() }
fn default_queue_spacing() -> f64 { 8.0 }
fn default_true() -> bool { true }

impl Default for SimulationRequest {
    fn default() -> Self {
        Self {
            border_config: BorderCrossingConfig::default(),
            simulation_config: None,
            phone_config: None,
            physics_config: None,
            physics_ranges: None,
            crossing_name: default_crossing_name(),
            direction: default_direction(),
            queue_spacing: default_queue_spacing(),
            geojson_path: None,
            use_dynamic_paths: default_true(),
            country_of_origin: None,
        }
    }
}

/// Response from starting a simulation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationStartResponse {
    /// Unique simulation ID
    pub simulation_id: String,
    /// Current status
    pub status: String,
    /// WebSocket URL for streaming
    pub websocket_url: String,
    /// Status message
    pub message: String,
}

/// Simulation status response
/// Matches Python SimulationStatus
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationStatus {
    /// Unique simulation ID
    pub simulation_id: String,
    /// Status: "running", "completed", "failed", "stopped", "cancelled"
    pub status: String,
    /// Progress from 0.0 to 1.0
    pub progress: f64,
    /// Current simulation time
    pub current_time: f64,
    /// Total arrivals
    pub total_arrivals: u32,
    /// Total completions
    pub total_completions: u32,
    /// Active car count (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_cars: Option<u32>,
    /// Optional message
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

/// Request to update time speed
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeSpeedUpdate {
    pub time_factor: f64,
}

/// Response from time speed update
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeSpeedResponse {
    pub status: String,
    pub time_factor: f64,
}

/// Request to add a service station
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddServiceNodeRequest {
    /// Queue ID to add node to
    pub queue_id: u32,
    /// Service rate in cars/minute
    #[serde(default = "default_service_rate")]
    pub service_rate: f64,
    /// Coefficient of variation for service time
    #[serde(default = "default_service_time_variation")]
    pub service_time_variation: f64,
}

fn default_service_rate() -> f64 { 3.0 }
fn default_service_time_variation() -> f64 { 0.2 }

/// Response from adding a service station
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddServiceNodeResponse {
    /// New station ID
    pub station_id: String,
    /// Queue ID it was added to
    pub queue_id: u32,
    /// Service rate
    pub service_rate: f64,
    /// Service time variation
    pub service_time_variation: f64,
}

/// Response from removing a service node
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemoveServiceNodeResponse {
    pub node_id: String,
    pub message: String,
}

/// Response from stopping a simulation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StopSimulationResponse {
    pub simulation_id: String,
    pub status: String,
    pub message: String,
    pub telemetry_records_saved: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub database_path: Option<String>,
}

/// Response from cancelling a simulation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CancelSimulationResponse {
    pub simulation_id: String,
    pub status: String,
}

/// Response from adding a car
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddCarResponse {
    pub car_id: u32,
    pub queue_id: u32,
    pub message: String,
}

/// Car detail response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CarDetailResponse {
    pub car_id: u32,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub queue_id: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub queue_position: Option<u32>,
    pub position: [f64; 2],
    pub velocity: f64,
    pub acceleration: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub arrival_time: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub queue_start_time: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub service_start_time: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub completion_time: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub wait_time: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub distance_traveled: Option<f64>,
}

/// Border crossing list response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BorderCrossingsResponse {
    pub crossings: Vec<BorderCrossingInfo>,
}

/// Border crossing info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BorderCrossingInfo {
    pub id: String,
    pub name: String,
    pub direction: String,
    pub path: String,
    pub description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_point: Option<[f64; 2]>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end_point: Option<[f64; 2]>,
    pub geometry_type: String,
}

/// Simulation state response (for real-time visualization)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationStateResponse {
    pub simulation_id: String,
    pub status: String,
    pub current_time: f64,
    pub cars: Vec<CarData>,
    pub service_nodes: Vec<ServiceNodeData>,
    pub statistics: SimulationStatistics,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub traffic_control_points: Option<Vec<serde_json::Value>>,
}

/// Car data for state response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CarData {
    pub car_id: u32,
    pub position: f64,
    pub velocity: f64,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub queue_id: Option<u32>,
}

/// Service node data for state response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceNodeData {
    pub node_id: String,
    pub queue_id: u32,
    pub is_busy: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub current_car_id: Option<u32>,
    pub service_rate: f64,
    pub total_served: u32,
    pub total_service_time: f64,
}

/// Simulation statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationStatistics {
    pub total_arrivals: u32,
    pub total_completions: u32,
    pub active_cars: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub average_wait_time: Option<f64>,
    pub simulation_time: f64,
}

/// API error response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiError {
    pub error: String,
    pub detail: String,
}

impl ApiError {
    pub fn new(error: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            error: error.into(),
            detail: detail.into(),
        }
    }

    pub fn not_found(detail: impl Into<String>) -> Self {
        Self::new("not_found", detail)
    }

    pub fn bad_request(detail: impl Into<String>) -> Self {
        Self::new("bad_request", detail)
    }

    pub fn internal_error(detail: impl Into<String>) -> Self {
        Self::new("internal_error", detail)
    }
}

/// Generate a new simulation ID
pub fn generate_simulation_id() -> String {
    Uuid::new_v4().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulation_request_default() {
        let request = SimulationRequest::default();
        assert_eq!(request.crossing_name, "paso_del_norte");
        assert_eq!(request.direction, "mx2usa");
        assert_eq!(request.queue_spacing, 8.0);
    }

    #[test]
    fn test_simulation_request_serialization() {
        let request = SimulationRequest::default();
        let json = serde_json::to_string(&request).unwrap();
        assert!(json.contains("border_config"));
        assert!(json.contains("crossing_name"));

        let parsed: SimulationRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(request.crossing_name, parsed.crossing_name);
    }

    #[test]
    fn test_simulation_request_parse_minimal() {
        let json = r#"{
            "border_config": {
                "num_queues": 2
            }
        }"#;

        let request: SimulationRequest = serde_json::from_str(json).unwrap();
        assert_eq!(request.border_config.num_queues, 2);
        assert_eq!(request.crossing_name, "paso_del_norte"); // default
    }

    #[test]
    fn test_simulation_status_serialization() {
        let status = SimulationStatus {
            simulation_id: "test-id".to_string(),
            status: "running".to_string(),
            progress: 0.5,
            current_time: 1800.0,
            total_arrivals: 100,
            total_completions: 50,
            active_cars: Some(50),
            message: None,
        };

        let json = serde_json::to_string(&status).unwrap();
        assert!(json.contains("running"));
        assert!(json.contains("0.5"));
    }

    #[test]
    fn test_time_speed_update() {
        let update = TimeSpeedUpdate { time_factor: 2.0 };
        let json = serde_json::to_string(&update).unwrap();
        assert!(json.contains("2.0"));
    }

    #[test]
    fn test_add_service_node_request() {
        let json = r#"{"queue_id": 1}"#;
        let request: AddServiceNodeRequest = serde_json::from_str(json).unwrap();
        assert_eq!(request.queue_id, 1);
        assert_eq!(request.service_rate, 3.0); // default
    }

    #[test]
    fn test_api_error() {
        let error = ApiError::not_found("Simulation not found");
        assert_eq!(error.error, "not_found");
        assert_eq!(error.detail, "Simulation not found");
    }

    #[test]
    fn test_generate_simulation_id() {
        let id1 = generate_simulation_id();
        let id2 = generate_simulation_id();
        assert_ne!(id1, id2);
        assert_eq!(id1.len(), 36); // UUID format
    }

    #[test]
    fn test_car_detail_response() {
        let response = CarDetailResponse {
            car_id: 42,
            status: "queued".to_string(),
            queue_id: Some(1),
            queue_position: Some(5),
            position: [-106.5, 31.75],
            velocity: 2.5,
            acceleration: 0.0,
            arrival_time: Some(100.0),
            queue_start_time: Some(110.0),
            service_start_time: None,
            completion_time: None,
            wait_time: Some(10.0),
            distance_traveled: Some(450.0),
        };

        let json = serde_json::to_string(&response).unwrap();
        assert!(json.contains("queued"));
        assert!(json.contains("42"));
    }

    #[test]
    fn test_simulation_state_response() {
        let response = SimulationStateResponse {
            simulation_id: "test-id".to_string(),
            status: "running".to_string(),
            current_time: 100.0,
            cars: vec![],
            service_nodes: vec![],
            statistics: SimulationStatistics {
                total_arrivals: 10,
                total_completions: 5,
                active_cars: 5,
                average_wait_time: Some(30.0),
                simulation_time: 100.0,
            },
            traffic_control_points: None,
        };

        let json = serde_json::to_string(&response).unwrap();
        assert!(json.contains("statistics"));
    }
}
