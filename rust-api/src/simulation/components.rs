//! ECS Components for the simulation engine
//!
//! This module defines all the components used in the Bevy ECS simulation.
//! Components are data containers attached to entities (cars, service nodes, etc.).

use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

/// Position component storing geographic coordinates in UTM meters
/// Used for precise physics calculations (x, y in meters)
#[derive(Component, Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct Position {
    /// X coordinate in UTM meters (easting)
    pub x: f64,
    /// Y coordinate in UTM meters (northing)
    pub y: f64,
}

impl Position {
    /// Create a new position
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }

    /// Calculate Euclidean distance to another position
    pub fn distance_to(&self, other: &Position) -> f64 {
        let dx = other.x - self.x;
        let dy = other.y - self.y;
        (dx * dx + dy * dy).sqrt()
    }
}

/// Velocity component storing velocity vector in m/s
#[derive(Component, Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct Velocity {
    /// Velocity in X direction (m/s)
    pub vx: f64,
    /// Velocity in Y direction (m/s)
    pub vy: f64,
}

impl Velocity {
    /// Create a new velocity
    pub fn new(vx: f64, vy: f64) -> Self {
        Self { vx, vy }
    }

    /// Get the speed (magnitude of velocity)
    pub fn speed(&self) -> f64 {
        (self.vx * self.vx + self.vy * self.vy).sqrt()
    }

    /// Create velocity from speed and direction angle (radians)
    pub fn from_speed_and_angle(speed: f64, angle: f64) -> Self {
        Self {
            vx: speed * angle.cos(),
            vy: speed * angle.sin(),
        }
    }

    /// Get the direction angle in radians
    pub fn angle(&self) -> f64 {
        self.vy.atan2(self.vx)
    }
}

/// Acceleration component storing acceleration vector in m/s^2
#[derive(Component, Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct Acceleration {
    /// Acceleration in X direction (m/s^2)
    pub ax: f64,
    /// Acceleration in Y direction (m/s^2)
    pub ay: f64,
}

impl Acceleration {
    /// Create a new acceleration
    pub fn new(ax: f64, ay: f64) -> Self {
        Self { ax, ay }
    }

    /// Get the magnitude of acceleration
    pub fn magnitude(&self) -> f64 {
        (self.ax * self.ax + self.ay * self.ay).sqrt()
    }

    /// Create acceleration from magnitude and direction angle (radians)
    pub fn from_magnitude_and_angle(magnitude: f64, angle: f64) -> Self {
        Self {
            ax: magnitude * angle.cos(),
            ay: magnitude * angle.sin(),
        }
    }
}

/// Car status enum matching Python implementation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
pub enum Status {
    /// Car is approaching the border crossing
    #[default]
    Approaching,
    /// Car is in queue waiting
    Queued,
    /// Car is being served at a booth
    Serving,
    /// Car has completed service and is exiting
    Completed,
}

impl Status {
    /// Convert to string representation matching Python
    pub fn as_str(&self) -> &'static str {
        match self {
            Status::Approaching => "approaching",
            Status::Queued => "queued",
            Status::Serving => "serving",
            Status::Completed => "completed",
        }
    }

    /// Parse from string
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "approaching" => Some(Status::Approaching),
            "queued" => Some(Status::Queued),
            "serving" => Some(Status::Serving),
            "completed" => Some(Status::Completed),
            _ => None,
        }
    }
}

/// Car status component
#[derive(Component, Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct CarStatus(pub Status);

impl CarStatus {
    pub fn new(status: Status) -> Self {
        Self(status)
    }

    pub fn is_approaching(&self) -> bool {
        self.0 == Status::Approaching
    }

    pub fn is_queued(&self) -> bool {
        self.0 == Status::Queued
    }

    pub fn is_serving(&self) -> bool {
        self.0 == Status::Serving
    }

    pub fn is_completed(&self) -> bool {
        self.0 == Status::Completed
    }
}

/// Queue membership component - tracks which queue a car belongs to
#[derive(Component, Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct QueueMembership {
    /// ID of the queue this car belongs to
    pub queue_id: u32,
    /// Position in the queue (1 = first/front)
    pub position: u32,
}

impl QueueMembership {
    pub fn new(queue_id: u32, position: u32) -> Self {
        Self { queue_id, position }
    }
}

/// Path component - waypoints for car movement
#[derive(Component, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Path {
    /// List of waypoints as (x, y) UTM coordinates
    pub waypoints: Vec<(f64, f64)>,
    /// Current waypoint index the car is moving toward
    pub current_index: usize,
    /// Total length of the path in meters
    pub total_length: f64,
    /// Current position along the path in meters
    pub position_along_path: f64,
}

impl Path {
    /// Create a new path from waypoints
    pub fn new(waypoints: Vec<(f64, f64)>) -> Self {
        let total_length = Self::calculate_length(&waypoints);
        Self {
            waypoints,
            current_index: 0,
            total_length,
            position_along_path: 0.0,
        }
    }

    /// Calculate total length of a path
    fn calculate_length(waypoints: &[(f64, f64)]) -> f64 {
        if waypoints.len() < 2 {
            return 0.0;
        }

        let mut length = 0.0;
        for i in 1..waypoints.len() {
            let (x1, y1) = waypoints[i - 1];
            let (x2, y2) = waypoints[i];
            let dx = x2 - x1;
            let dy = y2 - y1;
            length += (dx * dx + dy * dy).sqrt();
        }
        length
    }

    /// Get position and direction at a given distance along the path
    pub fn interpolate(&self, distance: f64) -> Option<(Position, f64)> {
        if self.waypoints.is_empty() {
            return None;
        }

        let distance = distance.clamp(0.0, self.total_length);
        let mut accumulated = 0.0;

        for i in 1..self.waypoints.len() {
            let (x1, y1) = self.waypoints[i - 1];
            let (x2, y2) = self.waypoints[i];
            let dx = x2 - x1;
            let dy = y2 - y1;
            let segment_length = (dx * dx + dy * dy).sqrt();

            if accumulated + segment_length >= distance {
                // Interpolate within this segment
                let t = if segment_length > 0.0 {
                    (distance - accumulated) / segment_length
                } else {
                    0.0
                };
                let x = x1 + t * dx;
                let y = y1 + t * dy;
                let angle = dy.atan2(dx);
                return Some((Position::new(x, y), angle));
            }

            accumulated += segment_length;
        }

        // Return last waypoint
        let (x, y) = self.waypoints.last()?;
        let angle = if self.waypoints.len() >= 2 {
            let (x1, y1) = self.waypoints[self.waypoints.len() - 2];
            (y - y1).atan2(x - x1)
        } else {
            0.0
        };
        Some((Position::new(*x, *y), angle))
    }

    /// Get the remaining distance to the end of the path
    pub fn remaining_distance(&self) -> f64 {
        (self.total_length - self.position_along_path).max(0.0)
    }
}

/// Car entity marker component
#[derive(Component, Debug, Clone, Copy, Default)]
pub struct Car {
    /// Unique car ID
    pub id: u32,
    /// Car length in meters (for collision detection)
    pub length: f64,
}

impl Car {
    pub fn new(id: u32) -> Self {
        Self {
            id,
            length: 4.5, // Default car length in meters
        }
    }

    pub fn with_length(id: u32, length: f64) -> Self {
        Self { id, length }
    }
}

/// Physics properties component - limits for car movement
#[derive(Component, Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PhysicsProperties {
    /// Maximum velocity in m/s
    pub max_velocity: f64,
    /// Maximum acceleration in m/s^2
    pub max_acceleration: f64,
    /// Maximum deceleration in m/s^2 (positive value)
    pub max_deceleration: f64,
    /// Queue movement velocity in m/s
    pub queue_velocity: f64,
    /// Preferred speed (with variance)
    pub preferred_speed: f64,
}

impl Default for PhysicsProperties {
    fn default() -> Self {
        Self {
            max_velocity: 13.4112,      // 30 mph in m/s
            max_acceleration: 0.75,     // m/s^2
            max_deceleration: 1.25,     // m/s^2
            queue_velocity: 1.34112,    // 3 mph in m/s
            preferred_speed: 13.4112,
        }
    }
}

impl PhysicsProperties {
    /// Create new physics properties with variance applied to speed
    pub fn with_speed_variance(mut self, variance_factor: f64) -> Self {
        self.preferred_speed = self.max_velocity * variance_factor;
        self
    }
}

/// Timing information for a car
#[derive(Component, Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct CarTiming {
    /// When the car arrived in the system
    pub arrival_time: Option<f64>,
    /// When the car first entered queued state
    pub queue_start_time: Option<f64>,
    /// When service started
    pub service_start_time: Option<f64>,
    /// When service completed
    pub completion_time: Option<f64>,
    /// When car exited the system
    pub exit_time: Option<f64>,
    /// When current status started
    pub status_start_time: Option<f64>,
}

impl CarTiming {
    /// Calculate wait time (queue_start to service_start)
    pub fn wait_time(&self) -> Option<f64> {
        match (self.queue_start_time, self.service_start_time) {
            (Some(queue), Some(service)) => Some(service - queue),
            _ => None,
        }
    }

    /// Calculate service time
    pub fn service_time(&self) -> Option<f64> {
        match (self.service_start_time, self.completion_time) {
            (Some(start), Some(end)) => Some(end - start),
            _ => None,
        }
    }

    /// Calculate total journey time
    pub fn total_journey_time(&self) -> Option<f64> {
        match (self.arrival_time, self.exit_time.or(self.completion_time)) {
            (Some(arrival), Some(end)) => Some(end - arrival),
            _ => None,
        }
    }
}

/// Service node component for booth entities
#[derive(Component, Debug, Clone)]
pub struct ServiceNode {
    /// Unique node ID
    pub node_id: String,
    /// Queue this node belongs to
    pub queue_id: u32,
    /// Service rate (cars per minute)
    pub service_rate: f64,
    /// Whether the node is currently serving a car
    pub is_busy: bool,
    /// ID of car currently being served
    pub current_car_id: Option<u32>,
    /// When service will complete
    pub service_completion_time: Option<f64>,
    /// Total cars served
    pub total_served: u32,
    /// Total service time
    pub total_service_time: f64,
}

impl ServiceNode {
    pub fn new(node_id: String, queue_id: u32, service_rate: f64) -> Self {
        Self {
            node_id,
            queue_id,
            service_rate,
            is_busy: false,
            current_car_id: None,
            service_completion_time: None,
            total_served: 0,
            total_service_time: 0.0,
        }
    }

    pub fn is_available(&self) -> bool {
        !self.is_busy
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    // ========== Position Tests ==========

    #[test]
    fn test_position_creation() {
        let pos = Position::new(100.0, 200.0);
        assert_eq!(pos.x, 100.0);
        assert_eq!(pos.y, 200.0);
    }

    #[test]
    fn test_position_default() {
        let pos = Position::default();
        assert_eq!(pos.x, 0.0);
        assert_eq!(pos.y, 0.0);
    }

    #[test]
    fn test_position_distance() {
        let p1 = Position::new(0.0, 0.0);
        let p2 = Position::new(3.0, 4.0);
        assert!((p1.distance_to(&p2) - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_position_distance_same_point() {
        let p = Position::new(10.0, 20.0);
        assert!((p.distance_to(&p)).abs() < 1e-10);
    }

    // ========== Velocity Tests ==========

    #[test]
    fn test_velocity_creation() {
        let vel = Velocity::new(5.0, 10.0);
        assert_eq!(vel.vx, 5.0);
        assert_eq!(vel.vy, 10.0);
    }

    #[test]
    fn test_velocity_speed() {
        let vel = Velocity::new(3.0, 4.0);
        assert!((vel.speed() - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_velocity_from_speed_and_angle() {
        let vel = Velocity::from_speed_and_angle(10.0, 0.0);
        assert!((vel.vx - 10.0).abs() < 1e-10);
        assert!(vel.vy.abs() < 1e-10);

        let vel2 = Velocity::from_speed_and_angle(10.0, PI / 2.0);
        assert!(vel2.vx.abs() < 1e-10);
        assert!((vel2.vy - 10.0).abs() < 1e-10);
    }

    #[test]
    fn test_velocity_angle() {
        let vel = Velocity::new(1.0, 0.0);
        assert!(vel.angle().abs() < 1e-10);

        let vel2 = Velocity::new(0.0, 1.0);
        assert!((vel2.angle() - PI / 2.0).abs() < 1e-10);
    }

    // ========== Acceleration Tests ==========

    #[test]
    fn test_acceleration_creation() {
        let acc = Acceleration::new(1.0, 2.0);
        assert_eq!(acc.ax, 1.0);
        assert_eq!(acc.ay, 2.0);
    }

    #[test]
    fn test_acceleration_magnitude() {
        let acc = Acceleration::new(3.0, 4.0);
        assert!((acc.magnitude() - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_acceleration_from_magnitude_and_angle() {
        let acc = Acceleration::from_magnitude_and_angle(5.0, 0.0);
        assert!((acc.ax - 5.0).abs() < 1e-10);
        assert!(acc.ay.abs() < 1e-10);
    }

    // ========== CarStatus Tests ==========

    #[test]
    fn test_car_status_creation() {
        let status = CarStatus::new(Status::Approaching);
        assert!(status.is_approaching());
        assert!(!status.is_queued());
        assert!(!status.is_serving());
        assert!(!status.is_completed());
    }

    #[test]
    fn test_car_status_default() {
        let status = CarStatus::default();
        assert!(status.is_approaching());
    }

    #[test]
    fn test_status_as_str() {
        assert_eq!(Status::Approaching.as_str(), "approaching");
        assert_eq!(Status::Queued.as_str(), "queued");
        assert_eq!(Status::Serving.as_str(), "serving");
        assert_eq!(Status::Completed.as_str(), "completed");
    }

    #[test]
    fn test_status_from_str() {
        assert_eq!(Status::from_str("approaching"), Some(Status::Approaching));
        assert_eq!(Status::from_str("QUEUED"), Some(Status::Queued));
        assert_eq!(Status::from_str("Serving"), Some(Status::Serving));
        assert_eq!(Status::from_str("completed"), Some(Status::Completed));
        assert_eq!(Status::from_str("invalid"), None);
    }

    // ========== QueueMembership Tests ==========

    #[test]
    fn test_queue_membership_creation() {
        let membership = QueueMembership::new(0, 3);
        assert_eq!(membership.queue_id, 0);
        assert_eq!(membership.position, 3);
    }

    // ========== Path Tests ==========

    #[test]
    fn test_path_creation() {
        let waypoints = vec![(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)];
        let path = Path::new(waypoints);
        assert!((path.total_length - 200.0).abs() < 1e-10);
        assert_eq!(path.current_index, 0);
        assert_eq!(path.position_along_path, 0.0);
    }

    #[test]
    fn test_path_empty() {
        let path = Path::new(vec![]);
        assert_eq!(path.total_length, 0.0);
        assert!(path.interpolate(0.0).is_none());
    }

    #[test]
    fn test_path_single_waypoint() {
        let path = Path::new(vec![(50.0, 50.0)]);
        assert_eq!(path.total_length, 0.0);
    }

    #[test]
    fn test_path_interpolate() {
        let waypoints = vec![(0.0, 0.0), (100.0, 0.0)];
        let path = Path::new(waypoints);

        // Start of path
        let (pos, angle) = path.interpolate(0.0).unwrap();
        assert!((pos.x - 0.0).abs() < 1e-10);
        assert!((pos.y - 0.0).abs() < 1e-10);
        assert!(angle.abs() < 1e-10); // Angle should be 0 (pointing right)

        // Middle of path
        let (pos, _) = path.interpolate(50.0).unwrap();
        assert!((pos.x - 50.0).abs() < 1e-10);
        assert!((pos.y - 0.0).abs() < 1e-10);

        // End of path
        let (pos, _) = path.interpolate(100.0).unwrap();
        assert!((pos.x - 100.0).abs() < 1e-10);
        assert!((pos.y - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_path_remaining_distance() {
        let waypoints = vec![(0.0, 0.0), (100.0, 0.0)];
        let mut path = Path::new(waypoints);
        assert!((path.remaining_distance() - 100.0).abs() < 1e-10);

        path.position_along_path = 30.0;
        assert!((path.remaining_distance() - 70.0).abs() < 1e-10);

        path.position_along_path = 100.0;
        assert!((path.remaining_distance()).abs() < 1e-10);
    }

    // ========== Car Tests ==========

    #[test]
    fn test_car_creation() {
        let car = Car::new(1);
        assert_eq!(car.id, 1);
        assert_eq!(car.length, 4.5);
    }

    #[test]
    fn test_car_with_length() {
        let car = Car::with_length(1, 5.0);
        assert_eq!(car.id, 1);
        assert_eq!(car.length, 5.0);
    }

    // ========== PhysicsProperties Tests ==========

    #[test]
    fn test_physics_properties_default() {
        let props = PhysicsProperties::default();
        assert!((props.max_velocity - 13.4112).abs() < 0.001);
        assert!((props.max_acceleration - 0.75).abs() < 0.001);
        assert!((props.max_deceleration - 1.25).abs() < 0.001);
        assert!((props.queue_velocity - 1.34112).abs() < 0.001);
    }

    #[test]
    fn test_physics_properties_with_variance() {
        let props = PhysicsProperties::default().with_speed_variance(0.9);
        assert!((props.preferred_speed - 13.4112 * 0.9).abs() < 0.001);
    }

    // ========== CarTiming Tests ==========

    #[test]
    fn test_car_timing_default() {
        let timing = CarTiming::default();
        assert!(timing.arrival_time.is_none());
        assert!(timing.wait_time().is_none());
    }

    #[test]
    fn test_car_timing_wait_time() {
        let timing = CarTiming {
            queue_start_time: Some(10.0),
            service_start_time: Some(50.0),
            ..Default::default()
        };
        assert_eq!(timing.wait_time(), Some(40.0));
    }

    #[test]
    fn test_car_timing_service_time() {
        let timing = CarTiming {
            service_start_time: Some(50.0),
            completion_time: Some(80.0),
            ..Default::default()
        };
        assert_eq!(timing.service_time(), Some(30.0));
    }

    #[test]
    fn test_car_timing_total_journey_time() {
        let timing = CarTiming {
            arrival_time: Some(0.0),
            exit_time: Some(100.0),
            ..Default::default()
        };
        assert_eq!(timing.total_journey_time(), Some(100.0));
    }

    // ========== ServiceNode Tests ==========

    #[test]
    fn test_service_node_creation() {
        let node = ServiceNode::new("q0_n0".to_string(), 0, 3.0);
        assert_eq!(node.node_id, "q0_n0");
        assert_eq!(node.queue_id, 0);
        assert_eq!(node.service_rate, 3.0);
        assert!(!node.is_busy);
        assert!(node.is_available());
    }

    #[test]
    fn test_service_node_availability() {
        let mut node = ServiceNode::new("q0_n0".to_string(), 0, 3.0);
        assert!(node.is_available());

        node.is_busy = true;
        assert!(!node.is_available());
    }
}
