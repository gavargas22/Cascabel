//! Simulation Engine - High-level API for running the ECS simulation
//!
//! This module provides a SimulationEngine struct that manages the ECS world,
//! schedules systems, and provides methods for controlling the simulation.

use bevy_ecs::prelude::*;

use super::components::*;
use super::resources::*;
use super::systems::*;

/// The main simulation engine that manages the ECS world and systems
pub struct SimulationEngine {
    /// The ECS world containing all entities and resources
    world: World,
    /// Schedule for physics updates
    physics_schedule: Schedule,
    /// Schedule for status transitions
    status_schedule: Schedule,
    /// Schedule for service node updates
    service_schedule: Schedule,
    /// Schedule for car removal
    removal_schedule: Schedule,
}

impl SimulationEngine {
    /// Create a new simulation engine with default configuration
    pub fn new() -> Self {
        Self::with_config(SimulationConfig::default())
    }

    /// Create a new simulation engine with custom configuration
    pub fn with_config(config: SimulationConfig) -> Self {
        let mut world = World::new();

        // Insert resources
        world.insert_resource(SimulationTime::new());
        world.insert_resource(config);
        world.insert_resource(SimulationStats::default());
        world.insert_resource(NextCarId::default());
        world.insert_resource(ArrivalSchedule::default());

        // Create schedules
        let mut physics_schedule = Schedule::default();
        physics_schedule.add_systems((physics_system, path_following_system).chain());

        let mut status_schedule = Schedule::default();
        status_schedule.add_systems(status_transition_system);

        let mut service_schedule = Schedule::default();
        service_schedule.add_systems(service_node_system);

        let mut removal_schedule = Schedule::default();
        removal_schedule.add_systems(car_removal_system);

        Self {
            world,
            physics_schedule,
            status_schedule,
            service_schedule,
            removal_schedule,
        }
    }

    /// Set the booth position (for single-booth scenarios)
    pub fn set_booth_position(&mut self, x: f64, y: f64) {
        self.world.insert_resource(BoothPosition::new(x, y));
    }

    /// Spawn a new car with a path
    pub fn spawn_car(&mut self, path: Path, queue_id: u32) -> u32 {
        let car_id = {
            let mut id_gen = self.world.resource_mut::<NextCarId>();
            id_gen.next()
        };

        let props = PhysicsProperties::default().with_speed_variance(
            0.9 + rand_variance() * 0.2, // 0.9 to 1.1
        );

        // Get starting position from path
        let (start_pos, start_angle) = path.interpolate(0.0).unwrap_or((Position::default(), 0.0));
        let initial_velocity = Velocity::from_speed_and_angle(props.preferred_speed, start_angle);

        self.world.spawn((
            Car::new(car_id),
            start_pos,
            initial_velocity,
            Acceleration::default(),
            CarStatus::new(Status::Approaching),
            QueueMembership::new(queue_id, 0),
            path,
            props,
            CarTiming {
                arrival_time: Some(self.current_time()),
                status_start_time: Some(self.current_time()),
                ..Default::default()
            },
        ));

        // Record arrival in stats
        {
            let mut stats = self.world.resource_mut::<SimulationStats>();
            stats.record_arrival();
        }

        car_id
    }

    /// Spawn a service node
    pub fn spawn_service_node(&mut self, node_id: String, queue_id: u32, service_rate: f64) {
        self.world.spawn(ServiceNode::new(node_id, queue_id, service_rate));
    }

    /// Advance the simulation by the given time delta (in seconds)
    pub fn step(&mut self, dt: f64) {
        // Update simulation time
        {
            let mut time = self.world.resource_mut::<SimulationTime>();
            time.advance(dt);
        }

        // Run physics
        self.physics_schedule.run(&mut self.world);

        // Run status transitions
        self.status_schedule.run(&mut self.world);

        // Run service node updates
        self.service_schedule.run(&mut self.world);

        // Run car removal
        self.removal_schedule.run(&mut self.world);
    }

    /// Get the current simulation time
    pub fn current_time(&self) -> f64 {
        self.world.resource::<SimulationTime>().elapsed
    }

    /// Get simulation statistics
    pub fn stats(&self) -> SimulationStats {
        self.world.resource::<SimulationStats>().clone()
    }

    /// Get the number of active cars
    pub fn active_car_count(&mut self) -> usize {
        self.world.query::<&Car>().iter(&self.world).count()
    }

    /// Set time scale for simulation speed control
    pub fn set_time_scale(&mut self, scale: f64) {
        let mut time = self.world.resource_mut::<SimulationTime>();
        time.set_time_scale(scale);
    }

    /// Get all car states for WebSocket broadcasting
    pub fn get_car_states(&mut self) -> Vec<CarStateSnapshot> {
        let mut states = Vec::new();

        for (car, pos, vel, status, timing) in self
            .world
            .query::<(&Car, &Position, &Velocity, &CarStatus, &CarTiming)>()
            .iter(&self.world)
        {
            states.push(CarStateSnapshot {
                id: car.id,
                x: pos.x,
                y: pos.y,
                velocity: vel.speed(),
                status: status.0,
                arrival_time: timing.arrival_time,
                service_start_time: timing.service_start_time,
                completion_time: timing.completion_time,
            });
        }

        states
    }

    /// Get position-only updates (compact format for high-frequency updates)
    pub fn get_position_updates(&mut self) -> Vec<PositionUpdate> {
        let mut updates = Vec::new();

        for (car, pos) in self.world.query::<(&Car, &Position)>().iter(&self.world) {
            updates.push(PositionUpdate {
                id: car.id,
                x: pos.x,
                y: pos.y,
            });
        }

        updates
    }

    /// Access the ECS world directly for advanced operations
    pub fn world(&self) -> &World {
        &self.world
    }

    /// Access the ECS world mutably for advanced operations
    pub fn world_mut(&mut self) -> &mut World {
        &mut self.world
    }
}

impl Default for SimulationEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Snapshot of a car's state for broadcasting
#[derive(Debug, Clone)]
pub struct CarStateSnapshot {
    pub id: u32,
    pub x: f64,
    pub y: f64,
    pub velocity: f64,
    pub status: Status,
    pub arrival_time: Option<f64>,
    pub service_start_time: Option<f64>,
    pub completion_time: Option<f64>,
}

/// Compact position update for high-frequency broadcasting
#[derive(Debug, Clone, Copy)]
pub struct PositionUpdate {
    pub id: u32,
    pub x: f64,
    pub y: f64,
}

/// Simple pseudo-random variance (0.0 to 1.0)
/// In production, use a proper RNG like rand crate
fn rand_variance() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .subsec_nanos();
    (nanos % 1000) as f64 / 1000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let mut engine = SimulationEngine::new();
        assert_eq!(engine.current_time(), 0.0);
        assert_eq!(engine.active_car_count(), 0);
    }

    #[test]
    fn test_engine_with_config() {
        let config = SimulationConfig {
            safe_distance: 5.0,
            num_queues: 3,
            ..Default::default()
        };
        let engine = SimulationEngine::with_config(config);
        assert_eq!(engine.current_time(), 0.0);
    }

    #[test]
    fn test_spawn_car() {
        let mut engine = SimulationEngine::new();
        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);

        let id = engine.spawn_car(path, 0);
        assert_eq!(id, 1);
        assert_eq!(engine.active_car_count(), 1);

        let stats = engine.stats();
        assert_eq!(stats.total_arrivals, 1);
        assert_eq!(stats.active_cars, 1);
    }

    #[test]
    fn test_spawn_multiple_cars() {
        let mut engine = SimulationEngine::new();

        for i in 0..10 {
            let path = Path::new(vec![(0.0, i as f64 * 100.0), (1000.0, i as f64 * 100.0)]);
            engine.spawn_car(path, 0);
        }

        assert_eq!(engine.active_car_count(), 10);
    }

    #[test]
    fn test_step_advances_time() {
        let mut engine = SimulationEngine::new();
        engine.step(0.1);
        assert!((engine.current_time() - 0.1).abs() < 0.001);

        engine.step(0.1);
        assert!((engine.current_time() - 0.2).abs() < 0.001);
    }

    #[test]
    fn test_time_scale() {
        let mut engine = SimulationEngine::new();
        engine.set_time_scale(2.0);
        engine.step(0.1);
        assert!((engine.current_time() - 0.2).abs() < 0.001);
    }

    #[test]
    fn test_car_moves_forward() {
        let mut engine = SimulationEngine::new();
        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
        engine.spawn_car(path, 0);

        // Run for 1 second
        for _ in 0..100 {
            engine.step(0.01);
        }

        let states = engine.get_car_states();
        assert_eq!(states.len(), 1);

        // Car should have moved forward (x > 0)
        assert!(states[0].x > 0.0, "Car should have moved forward");
    }

    #[test]
    fn test_get_position_updates() {
        let mut engine = SimulationEngine::new();

        for i in 0..5 {
            let path = Path::new(vec![(i as f64 * 10.0, 0.0), (1000.0, 0.0)]);
            engine.spawn_car(path, 0);
        }

        let updates = engine.get_position_updates();
        assert_eq!(updates.len(), 5);
    }

    #[test]
    fn test_service_node_spawn() {
        let mut engine = SimulationEngine::new();
        engine.spawn_service_node("booth_1".to_string(), 0, 3.0);

        // Verify service node was created
        let count = engine
            .world_mut()
            .query::<&ServiceNode>()
            .iter(engine.world())
            .count();
        assert_eq!(count, 1);
    }

    #[test]
    fn test_booth_position() {
        let mut engine = SimulationEngine::new();
        engine.set_booth_position(500.0, 0.0);

        let booth = engine.world().get_resource::<BoothPosition>();
        assert!(booth.is_some());
        assert_eq!(booth.unwrap().position.x, 500.0);
    }

    #[test]
    fn test_simulation_runs_without_crash() {
        let mut engine = SimulationEngine::new();
        engine.set_booth_position(1000.0, 0.0);
        engine.spawn_service_node("booth_1".to_string(), 0, 3.0);

        // Spawn 100 cars
        for i in 0..100 {
            let path = Path::new(vec![(0.0, (i % 3) as f64 * 10.0), (1000.0, (i % 3) as f64 * 10.0)]);
            engine.spawn_car(path, 0);
        }

        // Run for 100 seconds (10000 steps at 0.01s)
        for _ in 0..10000 {
            engine.step(0.01);
        }

        // Should complete without crashing
        assert!(engine.current_time() > 99.0);
    }
}
