//! ECS Resources for the simulation engine
//!
//! Resources are global data shared across all systems.

use bevy_ecs::prelude::*;
use serde::{Deserialize, Serialize};

/// Simulation time resource
#[derive(Resource, Debug, Clone, Default)]
pub struct SimulationTime {
    /// Total elapsed simulation time in seconds
    pub elapsed: f64,
    /// Time delta for current frame
    pub delta: f64,
    /// Time multiplier for speed control (1.0 = real-time)
    pub time_scale: f64,
}

impl SimulationTime {
    pub fn new() -> Self {
        Self {
            elapsed: 0.0,
            delta: 0.0,
            time_scale: 1.0,
        }
    }

    /// Advance time by the given delta (in real seconds)
    pub fn advance(&mut self, real_delta: f64) {
        self.delta = real_delta * self.time_scale;
        self.elapsed += self.delta;
    }

    /// Set time scale (speed multiplier)
    pub fn set_time_scale(&mut self, scale: f64) {
        self.time_scale = scale.max(0.0);
    }

    /// Get hour of day (0-23) for time-varying behavior
    pub fn hour_of_day(&self) -> u32 {
        ((self.elapsed / 3600.0) % 24.0) as u32
    }
}

/// Simulation configuration resource
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    /// Safe distance between cars in meters
    pub safe_distance: f64,
    /// Number of queues
    pub num_queues: u32,
    /// Maximum queue length
    pub max_queue_length: u32,
    /// Base arrival rate (cars per minute)
    pub arrival_rate: f64,
    /// Physics update rate in Hz
    pub physics_rate: f64,
    /// Detection range for collision detection in meters
    pub detection_range: f64,
    /// Distance past booth at which cars are removed
    pub removal_distance: f64,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            safe_distance: 3.0,
            num_queues: 1,
            max_queue_length: 50,
            arrival_rate: 2.0,
            physics_rate: 100.0,
            detection_range: 50.0,
            removal_distance: 5.0,
        }
    }
}

/// Simulation statistics resource
#[derive(Resource, Debug, Clone, Default)]
pub struct SimulationStats {
    /// Total cars that have arrived
    pub total_arrivals: u32,
    /// Total cars that have completed
    pub total_completions: u32,
    /// Current number of active cars
    pub active_cars: u32,
    /// Average wait time in seconds
    pub average_wait_time: f64,
    /// Current throughput (completions per minute)
    pub throughput: f64,
    /// List of wait times for calculating averages
    pub wait_times: Vec<f64>,
}

impl SimulationStats {
    /// Record a car arrival
    pub fn record_arrival(&mut self) {
        self.total_arrivals += 1;
        self.active_cars += 1;
    }

    /// Record a car completion with wait time
    pub fn record_completion(&mut self, wait_time: f64, current_time: f64) {
        self.total_completions += 1;
        self.active_cars = self.active_cars.saturating_sub(1);
        self.wait_times.push(wait_time);

        // Update average
        self.average_wait_time = self.wait_times.iter().sum::<f64>() / self.wait_times.len() as f64;

        // Update throughput
        if current_time > 0.0 {
            self.throughput = (self.total_completions as f64) / (current_time / 60.0);
        }
    }

    /// Record a car being removed (exited system)
    pub fn record_exit(&mut self) {
        self.active_cars = self.active_cars.saturating_sub(1);
    }
}

/// Next car ID counter resource
#[derive(Resource, Debug, Clone, Default)]
pub struct NextCarId(pub u32);

impl NextCarId {
    pub fn next(&mut self) -> u32 {
        self.0 += 1;
        self.0
    }
}

/// Booth position resource (for single-booth scenarios)
#[derive(Resource, Debug, Clone)]
pub struct BoothPosition {
    pub position: super::Position,
}

impl BoothPosition {
    pub fn new(x: f64, y: f64) -> Self {
        Self {
            position: super::Position::new(x, y),
        }
    }
}

/// Arrival timing resource
#[derive(Resource, Debug, Clone, Default)]
pub struct ArrivalSchedule {
    /// Next arrival time in simulation seconds
    pub next_arrival_time: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulation_time_advance() {
        let mut time = SimulationTime::new();
        time.advance(0.1);
        assert!((time.elapsed - 0.1).abs() < 1e-10);
        assert!((time.delta - 0.1).abs() < 1e-10);
    }

    #[test]
    fn test_simulation_time_scale() {
        let mut time = SimulationTime::new();
        time.set_time_scale(2.0);
        time.advance(0.1);
        assert!((time.elapsed - 0.2).abs() < 1e-10);
        assert!((time.delta - 0.2).abs() < 1e-10);
    }

    #[test]
    fn test_simulation_time_hour_of_day() {
        let mut time = SimulationTime::new();
        time.elapsed = 3600.0 * 6.0; // 6 hours
        assert_eq!(time.hour_of_day(), 6);

        time.elapsed = 3600.0 * 25.0; // 25 hours = 1 hour
        assert_eq!(time.hour_of_day(), 1);
    }

    #[test]
    fn test_simulation_config_default() {
        let config = SimulationConfig::default();
        assert_eq!(config.safe_distance, 3.0);
        assert_eq!(config.physics_rate, 100.0);
    }

    #[test]
    fn test_simulation_stats_arrivals() {
        let mut stats = SimulationStats::default();
        stats.record_arrival();
        assert_eq!(stats.total_arrivals, 1);
        assert_eq!(stats.active_cars, 1);
    }

    #[test]
    fn test_simulation_stats_completions() {
        let mut stats = SimulationStats::default();
        stats.record_arrival();
        stats.record_arrival();
        stats.record_completion(30.0, 60.0);
        assert_eq!(stats.total_completions, 1);
        assert_eq!(stats.active_cars, 1);
        assert!((stats.average_wait_time - 30.0).abs() < 0.001);
        assert!((stats.throughput - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_next_car_id() {
        let mut id_gen = NextCarId::default();
        assert_eq!(id_gen.next(), 1);
        assert_eq!(id_gen.next(), 2);
        assert_eq!(id_gen.next(), 3);
    }
}
