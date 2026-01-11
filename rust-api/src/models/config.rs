//! Configuration structures for simulation setup
//!
//! These structs map to the frontend TypeScript types and Python Pydantic models.

use serde::{Deserialize, Serialize};

/// Border crossing configuration
/// Matches Python BorderCrossingConfig and TypeScript BorderCrossingConfig
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BorderCrossingConfig {
    /// Number of queues/lanes
    #[serde(default = "default_num_queues")]
    pub num_queues: u32,
    /// Number of service nodes per queue
    #[serde(default = "default_nodes_per_queue")]
    pub nodes_per_queue: Vec<u32>,
    /// Overall arrival rate (cars/minute)
    #[serde(default = "default_arrival_rate")]
    pub arrival_rate: f64,
    /// Service rates for each node (cars/minute)
    #[serde(default = "default_service_rates")]
    pub service_rates: Vec<f64>,
    /// Queue assignment strategy
    #[serde(default)]
    pub queue_assignment: QueueAssignment,
    /// Safe distance between cars (meters)
    #[serde(default = "default_safe_distance")]
    pub safe_distance: f64,
    /// Maximum cars per queue
    #[serde(default = "default_max_queue_length")]
    pub max_queue_length: u32,
}

fn default_num_queues() -> u32 { 3 }
fn default_nodes_per_queue() -> Vec<u32> { vec![2, 3, 2] }
fn default_arrival_rate() -> f64 { 6.0 }
fn default_service_rates() -> Vec<f64> { vec![3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9] }
fn default_safe_distance() -> f64 { 8.0 }
fn default_max_queue_length() -> u32 { 50 }

impl Default for BorderCrossingConfig {
    fn default() -> Self {
        Self {
            num_queues: default_num_queues(),
            nodes_per_queue: default_nodes_per_queue(),
            arrival_rate: default_arrival_rate(),
            service_rates: default_service_rates(),
            queue_assignment: QueueAssignment::default(),
            safe_distance: default_safe_distance(),
            max_queue_length: default_max_queue_length(),
        }
    }
}

/// Queue assignment strategy
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "snake_case")]
pub enum QueueAssignment {
    Random,
    #[default]
    Shortest,
    RoundRobin,
}

/// Simulation configuration
/// Matches Python SimulationConfig
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SimulationConfig {
    /// Maximum simulation time (seconds)
    #[serde(default = "default_max_simulation_time")]
    pub max_simulation_time: f64,
    /// Time acceleration factor
    #[serde(default = "default_time_factor")]
    pub time_factor: f64,
    /// Generate telemetry data
    #[serde(default = "default_true")]
    pub enable_telemetry: bool,
    /// Track car positions
    #[serde(default = "default_true")]
    pub enable_position_tracking: bool,
}

fn default_max_simulation_time() -> f64 { 3600.0 }
fn default_time_factor() -> f64 { 1.0 }
fn default_true() -> bool { true }

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            max_simulation_time: default_max_simulation_time(),
            time_factor: default_time_factor(),
            enable_telemetry: default_true(),
            enable_position_tracking: default_true(),
        }
    }
}

/// Phone/device configuration for telemetry simulation
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PhoneConfig {
    /// Sensor sampling rate in Hz
    #[serde(default = "default_sampling_rate")]
    pub sampling_rate: f64,
    /// GPS noise parameters
    #[serde(default)]
    pub gps_noise: GpsNoise,
    /// Accelerometer noise std dev
    #[serde(default = "default_accelerometer_noise")]
    pub accelerometer_noise: f64,
    /// Gyroscope noise std dev
    #[serde(default = "default_gyro_noise")]
    pub gyro_noise: f64,
    /// Device orientation
    #[serde(default)]
    pub device_orientation: DeviceOrientation,
}

fn default_sampling_rate() -> f64 { 10.0 }
fn default_accelerometer_noise() -> f64 { 0.01 }
fn default_gyro_noise() -> f64 { 0.001 }

impl Default for PhoneConfig {
    fn default() -> Self {
        Self {
            sampling_rate: default_sampling_rate(),
            gps_noise: GpsNoise::default(),
            accelerometer_noise: default_accelerometer_noise(),
            gyro_noise: default_gyro_noise(),
            device_orientation: DeviceOrientation::default(),
        }
    }
}

/// GPS noise parameters
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GpsNoise {
    pub horizontal_accuracy: f64,
    pub vertical_accuracy: f64,
}

impl Default for GpsNoise {
    fn default() -> Self {
        Self {
            horizontal_accuracy: 5.0,
            vertical_accuracy: 3.0,
        }
    }
}

/// Device orientation
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "snake_case")]
pub enum DeviceOrientation {
    #[default]
    Portrait,
    Landscape,
}

/// Physics configuration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PhysicsConfig {
    /// Minimum speed (m/s) - slowest car
    #[serde(default = "default_min_speed")]
    pub min_speed_mps: f64,
    /// Maximum speed (m/s) - fastest car
    #[serde(default = "default_max_speed")]
    pub max_speed_mps: f64,
    /// Distance between cars (m)
    #[serde(default = "default_safe_distance_physics")]
    pub safe_distance_meters: f64,
    /// Maximum acceleration (m/s^2)
    #[serde(default = "default_max_acceleration")]
    pub max_acceleration: f64,
    /// Maximum deceleration (m/s^2)
    #[serde(default = "default_max_deceleration")]
    pub max_deceleration: f64,
}

fn default_min_speed() -> f64 { 12.1 } // ~27 mph
fn default_max_speed() -> f64 { 14.7 } // ~33 mph
fn default_safe_distance_physics() -> f64 { 3.0 }
fn default_max_acceleration() -> f64 { 0.75 }
fn default_max_deceleration() -> f64 { 1.25 }

impl Default for PhysicsConfig {
    fn default() -> Self {
        Self {
            min_speed_mps: default_min_speed(),
            max_speed_mps: default_max_speed(),
            safe_distance_meters: default_safe_distance_physics(),
            max_acceleration: default_max_acceleration(),
            max_deceleration: default_max_deceleration(),
        }
    }
}

/// Physics ranges for random selection
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PhysicsRanges {
    /// [min, max] m/s
    #[serde(default = "default_speed_range")]
    pub speed_range: [f64; 2],
    /// [min, max] meters
    #[serde(default = "default_safe_distance_range")]
    pub safe_distance_range: [f64; 2],
    /// [min, max] m/s^2
    #[serde(default = "default_acceleration_range")]
    pub acceleration_range: [f64; 2],
    /// [min, max] m/s^2
    #[serde(default = "default_deceleration_range")]
    pub deceleration_range: [f64; 2],
    /// [min, max] meters
    #[serde(default = "default_queue_spacing_range")]
    pub queue_spacing_range: [f64; 2],
}

fn default_speed_range() -> [f64; 2] { [12.0, 15.0] }
fn default_safe_distance_range() -> [f64; 2] { [2.0, 5.0] }
fn default_acceleration_range() -> [f64; 2] { [0.5, 1.0] }
fn default_deceleration_range() -> [f64; 2] { [1.0, 1.5] }
fn default_queue_spacing_range() -> [f64; 2] { [6.0, 10.0] }

impl Default for PhysicsRanges {
    fn default() -> Self {
        Self {
            speed_range: default_speed_range(),
            safe_distance_range: default_safe_distance_range(),
            acceleration_range: default_acceleration_range(),
            deceleration_range: default_deceleration_range(),
            queue_spacing_range: default_queue_spacing_range(),
        }
    }
}

/// Crossing configuration from bounding_boxes.json
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CrossingConfig {
    /// Bounding box [west, south, east, north]
    pub bounding_box: [f64; 4],
    /// Optional preferred queue geometry
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preferred_queue_geometry: Option<serde_json::Value>,
    /// Optional slowdown zones
    #[serde(skip_serializing_if = "Option::is_none")]
    pub slowdown_zones: Option<serde_json::Value>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_border_crossing_config_default() {
        let config = BorderCrossingConfig::default();
        assert_eq!(config.num_queues, 3);
        assert_eq!(config.nodes_per_queue, vec![2, 3, 2]);
        assert_eq!(config.arrival_rate, 6.0);
        assert_eq!(config.queue_assignment, QueueAssignment::Shortest);
    }

    #[test]
    fn test_border_crossing_config_serialization() {
        let config = BorderCrossingConfig::default();
        let json = serde_json::to_string(&config).unwrap();
        let parsed: BorderCrossingConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(config, parsed);
    }

    #[test]
    fn test_simulation_config_default() {
        let config = SimulationConfig::default();
        assert_eq!(config.max_simulation_time, 3600.0);
        assert_eq!(config.time_factor, 1.0);
        assert!(config.enable_telemetry);
        assert!(config.enable_position_tracking);
    }

    #[test]
    fn test_queue_assignment_serialization() {
        let json = r#""shortest""#;
        let assignment: QueueAssignment = serde_json::from_str(json).unwrap();
        assert_eq!(assignment, QueueAssignment::Shortest);

        let json = r#""random""#;
        let assignment: QueueAssignment = serde_json::from_str(json).unwrap();
        assert_eq!(assignment, QueueAssignment::Random);
    }

    #[test]
    fn test_physics_config_default() {
        let config = PhysicsConfig::default();
        assert!((config.min_speed_mps - 12.1).abs() < 0.001);
        assert!((config.max_speed_mps - 14.7).abs() < 0.001);
    }

    #[test]
    fn test_physics_ranges_default() {
        let ranges = PhysicsRanges::default();
        assert_eq!(ranges.speed_range, [12.0, 15.0]);
        assert_eq!(ranges.queue_spacing_range, [6.0, 10.0]);
    }

    #[test]
    fn test_phone_config_default() {
        let config = PhoneConfig::default();
        assert_eq!(config.sampling_rate, 10.0);
        assert_eq!(config.gps_noise.horizontal_accuracy, 5.0);
    }

    #[test]
    fn test_crossing_config_serialization() {
        let config = CrossingConfig {
            bounding_box: [-106.52833, 31.71882, -106.44473, 31.78589],
            preferred_queue_geometry: None,
            slowdown_zones: None,
        };
        let json = serde_json::to_string(&config).unwrap();
        assert!(json.contains("bounding_box"));
        let parsed: CrossingConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(config.bounding_box, parsed.bounding_box);
    }
}
