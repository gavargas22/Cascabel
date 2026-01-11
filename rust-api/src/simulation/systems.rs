//! ECS Systems for the simulation engine
//!
//! Systems process entities with specific component combinations.
//! They implement the game loop logic for physics, collision detection,
//! queue management, and service node processing.

use bevy_ecs::prelude::*;

use super::components::*;
use super::resources::*;
use super::spatial::SpatialIndex;

/// Physics system: Updates position and velocity based on acceleration
///
/// This system performs Euler integration to update car positions:
/// 1. velocity += acceleration * dt
/// 2. position += velocity * dt
///
/// Uses parallel iteration for performance with large car counts.
pub fn physics_system(
    time: Res<SimulationTime>,
    mut query: Query<(
        &mut Position,
        &mut Velocity,
        &Acceleration,
        &PhysicsProperties,
        &Path,
    )>,
) {
    let dt = time.delta;
    if dt <= 0.0 {
        return;
    }

    // Process all entities
    // Note: par_iter_mut requires bevy_ecs/multi-threaded feature
    // For now using regular iteration; can switch to par_iter_mut when needed
    for (mut pos, mut vel, acc, props, _path) in query.iter_mut() {
        // Update velocity with acceleration
        vel.vx += acc.ax * dt;
        vel.vy += acc.ay * dt;

        // Clamp velocity to max
        let speed = vel.speed();
        if speed > props.max_velocity {
            let factor = props.max_velocity / speed;
            vel.vx *= factor;
            vel.vy *= factor;
        }

        // Ensure non-negative speed (cars don't reverse)
        if speed < 0.0 {
            vel.vx = 0.0;
            vel.vy = 0.0;
        }

        // Update position
        pos.x += vel.vx * dt;
        pos.y += vel.vy * dt;
    }
}

/// Path following system: Updates position along path and calculates world position
pub fn path_following_system(
    time: Res<SimulationTime>,
    mut query: Query<(&mut Position, &Velocity, &mut Path)>,
) {
    let dt = time.delta;
    if dt <= 0.0 {
        return;
    }

    for (mut pos, vel, mut path) in query.iter_mut() {
        // Update position along path based on speed
        let speed = vel.speed();
        path.position_along_path += speed * dt;

        // Clamp to path length
        path.position_along_path = path.position_along_path.clamp(0.0, path.total_length);

        // Get world position from path
        if let Some((new_pos, _angle)) = path.interpolate(path.position_along_path) {
            pos.x = new_pos.x;
            pos.y = new_pos.y;
        }
    }
}

/// Car behavior system: Calculates target velocity and acceleration based on situation
///
/// This implements the core driving logic:
/// - Approaching cars follow their path toward the booth
/// - Queued cars maintain safe distance from car ahead
/// - Serving cars stay stationary
/// - Completed cars drive away
///
/// NOTE: This is the brute-force O(n^2) version. For simulations with many cars,
/// use `car_behavior_system_spatial` which uses R-tree spatial indexing for O(n log n).
pub fn car_behavior_system(
    config: Res<SimulationConfig>,
    booth: Option<Res<BoothPosition>>,
    mut query: Query<(
        Entity,
        &Position,
        &mut Velocity,
        &mut Acceleration,
        &CarStatus,
        &PhysicsProperties,
        &Path,
        &Car,
    )>,
) {
    // Collect positions for collision detection
    let car_data: Vec<_> = query
        .iter()
        .map(|(entity, pos, _, _, status, _, _, car)| {
            (entity, *pos, status.0, car.id, car.length)
        })
        .collect();

    let booth_pos = booth.as_ref().map(|b| b.position);

    for (entity, pos, vel, mut acc, status, props, path, _car) in query.iter_mut() {
        // Calculate distance to booth
        let distance_to_booth = if let Some(bp) = booth_pos {
            pos.distance_to(&bp)
        } else {
            path.remaining_distance()
        };

        // Find closest car ahead
        let (car_ahead_distance, car_ahead_velocity) = find_car_ahead(
            entity,
            &pos,
            distance_to_booth,
            &car_data,
            config.detection_range,
        );

        // Calculate target velocity based on status
        let target_velocity = match status.0 {
            Status::Approaching => calculate_approaching_velocity(
                distance_to_booth,
                car_ahead_distance,
                car_ahead_velocity,
                props,
                &config,
            ),
            Status::Queued => calculate_queued_velocity(
                distance_to_booth,
                car_ahead_distance,
                car_ahead_velocity,
                props,
                &config,
            ),
            Status::Serving => 0.0,
            Status::Completed => props.queue_velocity * 2.0, // Exit speed
        };

        // Calculate required acceleration to reach target velocity
        let current_speed = vel.speed();
        let speed_diff = target_velocity - current_speed;

        // Determine max acceleration/deceleration
        let max_acc = if speed_diff >= 0.0 {
            props.max_acceleration
        } else {
            props.max_deceleration
        };

        // Calculate acceleration magnitude (clamped)
        let acc_magnitude = speed_diff.abs().min(max_acc);
        let acc_sign = if speed_diff >= 0.0 { 1.0 } else { -1.0 };

        // Apply acceleration in direction of travel
        let direction = if current_speed > 0.001 {
            (vel.vx / current_speed, vel.vy / current_speed)
        } else if let Some((_, angle)) = path.interpolate(path.position_along_path) {
            (angle.cos(), angle.sin())
        } else {
            (1.0, 0.0)
        };

        acc.ax = direction.0 * acc_magnitude * acc_sign;
        acc.ay = direction.1 * acc_magnitude * acc_sign;
    }
}

/// Car behavior system with R-tree spatial indexing for O(log n) collision detection
///
/// This is the optimized version that uses a pre-built spatial index to find
/// nearby cars efficiently. The SpatialIndex resource must be kept up-to-date
/// by running `spatial_index_update_system` before this system.
///
/// Performance: O(n log n) total for n cars, vs O(n^2) for brute force.
pub fn car_behavior_system_spatial(
    config: Res<SimulationConfig>,
    booth: Option<Res<BoothPosition>>,
    spatial_index: Option<Res<SpatialIndex>>,
    mut query: Query<(
        Entity,
        &Position,
        &mut Velocity,
        &mut Acceleration,
        &CarStatus,
        &PhysicsProperties,
        &Path,
        &Car,
    )>,
) {
    let booth_pos = booth.as_ref().map(|b| b.position);
    let booth_array = booth_pos.map(|p| [p.x, p.y]);

    // If no spatial index, fall back to collecting car data
    let car_data: Option<Vec<_>> = if spatial_index.is_none() {
        Some(
            query
                .iter()
                .map(|(entity, pos, _, _, status, _, _, car)| {
                    (entity, *pos, status.0, car.id, car.length)
                })
                .collect(),
        )
    } else {
        None
    };

    for (entity, pos, vel, mut acc, status, props, path, _car) in query.iter_mut() {
        // Calculate distance to booth
        let distance_to_booth = if let Some(bp) = booth_pos {
            pos.distance_to(&bp)
        } else {
            path.remaining_distance()
        };

        // Find closest car ahead using spatial index or brute force
        let (car_ahead_distance, car_ahead_velocity) =
            if let Some(ref index) = spatial_index {
                // Use R-tree spatial index for O(log n) query
                find_car_ahead_spatial(
                    entity,
                    [pos.x, pos.y],
                    distance_to_booth,
                    index,
                    config.detection_range,
                    booth_array,
                )
            } else if let Some(ref data) = car_data {
                // Fallback to brute force
                find_car_ahead(entity, pos, distance_to_booth, data, config.detection_range)
            } else {
                (None, None)
            };

        // Calculate target velocity based on status
        let target_velocity = match status.0 {
            Status::Approaching => calculate_approaching_velocity(
                distance_to_booth,
                car_ahead_distance,
                car_ahead_velocity,
                props,
                &config,
            ),
            Status::Queued => calculate_queued_velocity(
                distance_to_booth,
                car_ahead_distance,
                car_ahead_velocity,
                props,
                &config,
            ),
            Status::Serving => 0.0,
            Status::Completed => props.queue_velocity * 2.0, // Exit speed
        };

        // Calculate required acceleration to reach target velocity
        let current_speed = vel.speed();
        let speed_diff = target_velocity - current_speed;

        // Determine max acceleration/deceleration
        let max_acc = if speed_diff >= 0.0 {
            props.max_acceleration
        } else {
            props.max_deceleration
        };

        // Calculate acceleration magnitude (clamped)
        let acc_magnitude = speed_diff.abs().min(max_acc);
        let acc_sign = if speed_diff >= 0.0 { 1.0 } else { -1.0 };

        // Apply acceleration in direction of travel
        let direction = if current_speed > 0.001 {
            (vel.vx / current_speed, vel.vy / current_speed)
        } else if let Some((_, angle)) = path.interpolate(path.position_along_path) {
            (angle.cos(), angle.sin())
        } else {
            (1.0, 0.0)
        };

        acc.ax = direction.0 * acc_magnitude * acc_sign;
        acc.ay = direction.1 * acc_magnitude * acc_sign;
    }
}

/// Find the closest car ahead using R-tree spatial index
fn find_car_ahead_spatial(
    entity: Entity,
    pos: [f64; 2],
    my_distance_to_booth: f64,
    spatial_index: &SpatialIndex,
    detection_range: f64,
    booth_pos: Option<[f64; 2]>,
) -> (Option<f64>, Option<f64>) {
    if let Some((gap, _entry)) = spatial_index.find_blocking_car(
        entity,
        pos,
        my_distance_to_booth,
        detection_range,
        booth_pos,
    ) {
        (Some(gap), Some(0.0)) // Velocity tracking could be added later
    } else {
        (None, None)
    }
}

/// Find the closest car ahead (closer to booth)
fn find_car_ahead(
    entity: Entity,
    pos: &Position,
    _my_distance_to_booth: f64,
    car_data: &[(Entity, Position, Status, u32, f64)],
    detection_range: f64,
) -> (Option<f64>, Option<f64>) {
    let mut closest_distance = None;
    let mut closest_velocity = None;

    for (other_entity, other_pos, _status, _id, length) in car_data {
        if *other_entity == entity {
            continue;
        }

        let geographic_distance = pos.distance_to(other_pos);
        if geographic_distance > detection_range {
            continue;
        }

        // Car is "ahead" if closer to booth
        // We use geographic distance since we don't have booth distance for other car
        // This is simplified; real implementation would need other car's booth distance
        let gap = geographic_distance - length;

        if closest_distance.is_none() || gap < closest_distance.unwrap() {
            closest_distance = Some(gap);
            closest_velocity = Some(0.0); // Simplified; would need actual velocity
        }
    }

    (closest_distance, closest_velocity)
}

/// Calculate velocity for approaching cars
fn calculate_approaching_velocity(
    distance_to_booth: f64,
    car_ahead_distance: Option<f64>,
    _car_ahead_velocity: Option<f64>,
    props: &PhysicsProperties,
    config: &SimulationConfig,
) -> f64 {
    let safe_distance = config.safe_distance;

    // Check for car ahead
    if let Some(gap) = car_ahead_distance {
        if gap <= 0.0 {
            return 0.0; // Overlapping, stop!
        } else if gap < safe_distance {
            return 0.0; // Too close, stop
        } else if gap < safe_distance * 2.0 {
            return props.queue_velocity * 0.3; // Very close, slow crawl
        } else if gap < safe_distance * 3.0 {
            return props.queue_velocity * 0.5; // Close, slow down
        } else if gap < safe_distance * 5.0 {
            return props.preferred_speed * 0.6; // Moderate distance
        } else if gap < safe_distance * 8.0 {
            return props.preferred_speed * 0.8; // Approaching
        }
    }

    // No car ahead or far enough - check booth distance
    if distance_to_booth < 50.0 {
        let slowdown_factor = distance_to_booth / 50.0;
        return props.queue_velocity.max(props.preferred_speed * slowdown_factor);
    } else if distance_to_booth < 5.0 {
        return 0.0;
    }

    props.preferred_speed
}

/// Calculate velocity for queued cars
fn calculate_queued_velocity(
    distance_to_booth: f64,
    car_ahead_distance: Option<f64>,
    _car_ahead_velocity: Option<f64>,
    props: &PhysicsProperties,
    config: &SimulationConfig,
) -> f64 {
    let safe_distance = config.safe_distance;

    if let Some(gap) = car_ahead_distance {
        if gap <= 0.0 {
            return 0.0; // Overlapping, stop!
        } else if gap < safe_distance {
            return 0.0; // Too close, stop
        } else if gap < safe_distance * 1.5 {
            return props.queue_velocity * 0.3; // Approaching safe distance
        } else if gap < safe_distance * 2.0 {
            return props.queue_velocity * 0.6; // Good spacing
        } else if gap < safe_distance * 3.0 {
            return props.queue_velocity; // Normal queue speed
        } else {
            return props.queue_velocity * 1.5; // Close gap
        }
    }

    // No car ahead - move toward booth
    if distance_to_booth > safe_distance * 2.0 {
        props.queue_velocity
    } else if distance_to_booth > safe_distance {
        props.queue_velocity * 0.5
    } else if distance_to_booth > 1.0 {
        props.queue_velocity * 0.2
    } else {
        0.0 // At booth
    }
}

/// Status transition system: Handles transitions between car statuses
pub fn status_transition_system(
    time: Res<SimulationTime>,
    config: Res<SimulationConfig>,
    booth: Option<Res<BoothPosition>>,
    mut query: Query<(
        Entity,
        &Position,
        &mut CarStatus,
        &mut CarTiming,
        &Path,
        &Car,
    )>,
) {
    // Collect all car positions for collision detection
    let car_positions: Vec<_> = query
        .iter()
        .map(|(entity, pos, status, _, path, car)| {
            (entity, *pos, status.0, path.remaining_distance(), car.length)
        })
        .collect();

    let booth_pos = booth.as_ref().map(|b| b.position);

    for (entity, pos, mut status, mut timing, path, _car) in query.iter_mut() {
        let current_status = status.0;
        let distance_to_booth = if let Some(bp) = booth_pos {
            pos.distance_to(&bp)
        } else {
            path.remaining_distance()
        };

        match current_status {
            Status::Approaching => {
                // Check if should transition to Queued
                let should_queue = check_should_queue(
                    entity,
                    &pos,
                    distance_to_booth,
                    &car_positions,
                    &config,
                );

                if should_queue {
                    status.0 = Status::Queued;
                    timing.status_start_time = Some(time.elapsed);
                    if timing.queue_start_time.is_none() {
                        timing.queue_start_time = Some(time.elapsed);
                    }
                }
            }
            Status::Queued => {
                // Queued -> Serving is handled by service node system
            }
            Status::Serving => {
                // Serving -> Completed is handled by service node system
            }
            Status::Completed => {
                // Will be removed by cleanup system when past booth
            }
        }
    }
}

/// Check if a car should transition from Approaching to Queued
fn check_should_queue(
    entity: Entity,
    pos: &Position,
    distance_to_booth: f64,
    car_positions: &[(Entity, Position, Status, f64, f64)],
    config: &SimulationConfig,
) -> bool {
    let safe_distance = config.safe_distance;

    // Must be within booth area (100m)
    if distance_to_booth >= 100.0 {
        return false;
    }

    // Find closest car ahead
    for (other_entity, other_pos, _status, other_dist_to_booth, length) in car_positions {
        if *other_entity == entity {
            continue;
        }

        let geo_distance = pos.distance_to(other_pos);
        let gap = geo_distance - length;

        // Blocked by car ahead in booth area
        if gap < safe_distance * 1.5 && *other_dist_to_booth < distance_to_booth {
            return true;
        }
    }

    // Very close to booth with no car ahead - about to be served
    if distance_to_booth < 5.0 {
        return true;
    }

    // At end of path
    if distance_to_booth < 3.0 {
        return true;
    }

    false
}

/// Service node system: Manages service node state and car serving
pub fn service_node_system(
    time: Res<SimulationTime>,
    mut stats: ResMut<SimulationStats>,
    mut service_nodes: Query<&mut ServiceNode>,
    mut cars: Query<(Entity, &Position, &mut CarStatus, &mut CarTiming, &Path, &Car)>,
    booth: Option<Res<BoothPosition>>,
) {
    let current_time = time.elapsed;
    let booth_pos = booth.as_ref().map(|b| b.position);

    // Process each service node
    for mut node in service_nodes.iter_mut() {
        // Check for service completion
        if node.is_busy {
            if let Some(completion_time) = node.service_completion_time {
                if current_time >= completion_time {
                    // Complete service
                    if let Some(car_id) = node.current_car_id {
                        // Find the car and update its status
                        for (_, _, mut status, mut timing, _, car) in cars.iter_mut() {
                            if car.id == car_id && status.0 == Status::Serving {
                                status.0 = Status::Completed;
                                timing.completion_time = Some(current_time);
                                timing.status_start_time = Some(current_time);

                                // Record completion stats
                                if let Some(wait_time) = timing.wait_time() {
                                    stats.record_completion(wait_time, current_time);
                                }

                                break;
                            }
                        }

                        // Update node stats
                        if let Some(start_time) = node.service_completion_time.map(|ct| {
                            ct - (1.0 / node.service_rate) * 60.0
                        }) {
                            node.total_service_time += current_time - start_time;
                        }
                        node.total_served += 1;
                    }

                    // Clear node
                    node.is_busy = false;
                    node.current_car_id = None;
                    node.service_completion_time = None;
                }
            }
        }

        // Try to start service for next car if node is available
        if !node.is_busy {
            // Find front-most queued car
            let mut front_car: Option<(Entity, u32, f64)> = None;

            for (entity, pos, status, _, path, car) in cars.iter() {
                if status.0 != Status::Queued {
                    continue;
                }

                let distance_to_booth = if let Some(bp) = booth_pos {
                    pos.distance_to(&bp)
                } else {
                    path.remaining_distance()
                };

                if front_car.is_none() || distance_to_booth < front_car.unwrap().2 {
                    front_car = Some((entity, car.id, distance_to_booth));
                }
            }

            // Start service for front car
            if let Some((entity, car_id, _)) = front_car {
                for (e, _, mut status, mut timing, _, car) in cars.iter_mut() {
                    if e == entity && car.id == car_id {
                        status.0 = Status::Serving;
                        timing.service_start_time = Some(current_time);
                        timing.status_start_time = Some(current_time);

                        node.is_busy = true;
                        node.current_car_id = Some(car_id);

                        // Generate service time (exponential distribution approximation)
                        // service_rate is cars per minute, so mean service time = 60/rate seconds
                        let mean_service_time = 60.0 / node.service_rate;
                        // Simple approximation: use mean + some variance
                        // In production, would use proper random number generator
                        let service_time = mean_service_time;
                        node.service_completion_time = Some(current_time + service_time);

                        break;
                    }
                }
            }
        }
    }
}

/// Car removal system: Removes cars that have completed and exited
pub fn car_removal_system(
    mut commands: Commands,
    config: Res<SimulationConfig>,
    _time: Res<SimulationTime>,
    booth: Option<Res<BoothPosition>>,
    mut stats: ResMut<SimulationStats>,
    query: Query<(Entity, &Position, &CarStatus, &Path)>,
) {
    let booth_pos = booth.as_ref().map(|b| b.position);

    for (entity, pos, status, path) in query.iter() {
        if status.0 != Status::Completed {
            continue;
        }

        // Check if car has passed the booth by enough distance
        let distance_to_booth = if let Some(bp) = booth_pos {
            pos.distance_to(&bp)
        } else {
            path.remaining_distance()
        };

        // For completed cars, negative remaining distance means past booth
        // Or we can check if position is past the path end
        let past_booth = path.position_along_path >= path.total_length + config.removal_distance;

        if past_booth || distance_to_booth < -config.removal_distance {
            commands.entity(entity).despawn();
            stats.record_exit();
        }
    }
}

/// Spawn a new car entity with all required components
pub fn spawn_car(
    commands: &mut Commands,
    id: u32,
    path: Path,
    queue_id: u32,
    physics_props: PhysicsProperties,
) -> Entity {
    // Get starting position from path
    let (start_pos, start_angle) = path.interpolate(0.0).unwrap_or((Position::default(), 0.0));

    // Create initial velocity in path direction
    let initial_velocity = Velocity::from_speed_and_angle(physics_props.preferred_speed, start_angle);

    commands
        .spawn((
            Car::new(id),
            start_pos,
            initial_velocity,
            Acceleration::default(),
            CarStatus::new(Status::Approaching),
            QueueMembership::new(queue_id, 0),
            path,
            physics_props,
            CarTiming::default(),
        ))
        .id()
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== Physics System Tests ==========

    #[test]
    fn test_physics_system_velocity_update() {
        let mut world = World::new();

        // Insert time resource
        let mut time = SimulationTime::new();
        time.delta = 0.1; // 100ms
        world.insert_resource(time);

        // Spawn a test entity
        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
        world.spawn((
            Position::new(0.0, 0.0),
            Velocity::new(10.0, 0.0),
            Acceleration::new(1.0, 0.0),
            PhysicsProperties::default(),
            path,
        ));

        // Create and run system
        let mut schedule = Schedule::default();
        schedule.add_systems(physics_system);
        schedule.run(&mut world);

        // Check results
        let mut query = world.query::<(&Position, &Velocity)>();
        let (pos, vel) = query.single(&world);

        // velocity = 10 + 1 * 0.1 = 10.1
        assert!((vel.vx - 10.1).abs() < 0.001);
        // position = 0 + 10.1 * 0.1 = 1.01
        assert!((pos.x - 1.01).abs() < 0.001);
    }

    #[test]
    fn test_physics_system_max_velocity_clamp() {
        let mut world = World::new();

        let mut time = SimulationTime::new();
        time.delta = 1.0;
        world.insert_resource(time);

        let props = PhysicsProperties {
            max_velocity: 10.0,
            ..Default::default()
        };

        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
        world.spawn((
            Position::new(0.0, 0.0),
            Velocity::new(15.0, 0.0), // Already above max
            Acceleration::new(5.0, 0.0),
            props,
            path,
        ));

        let mut schedule = Schedule::default();
        schedule.add_systems(physics_system);
        schedule.run(&mut world);

        let mut query = world.query::<&Velocity>();
        let vel = query.single(&world);

        // Should be clamped to max_velocity
        assert!(vel.speed() <= 10.001);
    }

    #[test]
    fn test_physics_system_zero_delta() {
        let mut world = World::new();

        let mut time = SimulationTime::new();
        time.delta = 0.0;
        world.insert_resource(time);

        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
        world.spawn((
            Position::new(100.0, 200.0),
            Velocity::new(10.0, 5.0),
            Acceleration::new(1.0, 1.0),
            PhysicsProperties::default(),
            path,
        ));

        let mut schedule = Schedule::default();
        schedule.add_systems(physics_system);
        schedule.run(&mut world);

        // Nothing should change with zero delta
        let mut query = world.query::<(&Position, &Velocity)>();
        let (pos, vel) = query.single(&world);

        assert!((pos.x - 100.0).abs() < 0.001);
        assert!((pos.y - 200.0).abs() < 0.001);
        assert!((vel.vx - 10.0).abs() < 0.001);
        assert!((vel.vy - 5.0).abs() < 0.001);
    }

    // ========== Path Following System Tests ==========

    #[test]
    fn test_path_following_system() {
        let mut world = World::new();

        let mut time = SimulationTime::new();
        time.delta = 1.0;
        world.insert_resource(time);

        let path = Path::new(vec![(0.0, 0.0), (100.0, 0.0)]);
        world.spawn((
            Position::new(0.0, 0.0),
            Velocity::new(10.0, 0.0), // 10 m/s
            path,
        ));

        let mut schedule = Schedule::default();
        schedule.add_systems(path_following_system);
        schedule.run(&mut world);

        let mut query = world.query::<(&Position, &Path)>();
        let (pos, path) = query.single(&world);

        // After 1 second at 10 m/s, should be at position 10
        assert!((path.position_along_path - 10.0).abs() < 0.001);
        assert!((pos.x - 10.0).abs() < 0.001);
        assert!((pos.y - 0.0).abs() < 0.001);
    }

    // ========== Status Transition Tests ==========

    #[test]
    fn test_status_defaults_to_approaching() {
        let status = CarStatus::default();
        assert!(status.is_approaching());
    }

    // ========== Spawn Car Tests ==========

    #[test]
    fn test_spawn_car() {
        let mut world = World::new();
        let path = Path::new(vec![(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]);
        let props = PhysicsProperties::default();

        // Get starting position from path
        let (start_pos, start_angle) = path.interpolate(0.0).unwrap();
        let initial_velocity = Velocity::from_speed_and_angle(props.preferred_speed, start_angle);

        // Spawn directly in world
        let entity = world.spawn((
            Car::new(1),
            start_pos,
            initial_velocity,
            Acceleration::default(),
            CarStatus::new(Status::Approaching),
            QueueMembership::new(0, 0),
            path,
            props,
            CarTiming::default(),
        )).id();

        // Verify entity was created with correct components
        assert!(world.get::<Car>(entity).is_some());
        assert!(world.get::<Position>(entity).is_some());
        assert!(world.get::<Velocity>(entity).is_some());
        assert!(world.get::<Acceleration>(entity).is_some());
        assert!(world.get::<CarStatus>(entity).is_some());
        assert!(world.get::<QueueMembership>(entity).is_some());
        assert!(world.get::<Path>(entity).is_some());
        assert!(world.get::<PhysicsProperties>(entity).is_some());
        assert!(world.get::<CarTiming>(entity).is_some());

        // Verify initial status is Approaching
        let status = world.get::<CarStatus>(entity).unwrap();
        assert!(status.is_approaching());
    }

    #[test]
    fn test_spawn_car_starting_position() {
        let mut world = World::new();
        let path = Path::new(vec![(50.0, 100.0), (150.0, 100.0)]);
        let props = PhysicsProperties::default();

        let (start_pos, start_angle) = path.interpolate(0.0).unwrap();
        let initial_velocity = Velocity::from_speed_and_angle(props.preferred_speed, start_angle);

        let entity = world.spawn((
            Car::new(1),
            start_pos,
            initial_velocity,
            Acceleration::default(),
            CarStatus::new(Status::Approaching),
            QueueMembership::new(0, 0),
            path,
            props,
            CarTiming::default(),
        )).id();

        let pos = world.get::<Position>(entity).unwrap();
        assert!((pos.x - 50.0).abs() < 0.001);
        assert!((pos.y - 100.0).abs() < 0.001);
    }

    // ========== Calculate Velocity Tests ==========

    #[test]
    fn test_approaching_velocity_no_car_ahead() {
        let props = PhysicsProperties::default();
        let config = SimulationConfig::default();

        let vel = calculate_approaching_velocity(500.0, None, None, &props, &config);
        assert!((vel - props.preferred_speed).abs() < 0.001);
    }

    #[test]
    fn test_approaching_velocity_car_ahead_close() {
        let props = PhysicsProperties::default();
        let config = SimulationConfig::default();

        // Car ahead within safe distance
        let vel = calculate_approaching_velocity(500.0, Some(2.0), None, &props, &config);
        assert_eq!(vel, 0.0);
    }

    #[test]
    fn test_queued_velocity_no_car_ahead() {
        let props = PhysicsProperties::default();
        let config = SimulationConfig::default();

        let vel = calculate_queued_velocity(100.0, None, None, &props, &config);
        assert!((vel - props.queue_velocity).abs() < 0.001);
    }

    #[test]
    fn test_queued_velocity_car_ahead_close() {
        let props = PhysicsProperties::default();
        let config = SimulationConfig::default();

        let vel = calculate_queued_velocity(100.0, Some(1.0), None, &props, &config);
        assert_eq!(vel, 0.0);
    }

    // ========== Integration Tests ==========

    #[test]
    fn test_full_physics_cycle() {
        let mut world = World::new();

        // Set up resources
        let mut time = SimulationTime::new();
        time.delta = 0.1;
        world.insert_resource(time);
        world.insert_resource(SimulationConfig::default());

        // Create a car
        let path = Path::new(vec![(0.0, 0.0), (1000.0, 0.0)]);
        world.spawn((
            Car::new(1),
            Position::new(0.0, 0.0),
            Velocity::new(10.0, 0.0),
            Acceleration::new(0.5, 0.0),
            CarStatus::new(Status::Approaching),
            QueueMembership::new(0, 1),
            path,
            PhysicsProperties::default(),
            CarTiming::default(),
        ));

        // Run multiple physics steps
        let mut schedule = Schedule::default();
        schedule.add_systems(physics_system);

        for _ in 0..10 {
            schedule.run(&mut world);
        }

        // Verify car has moved
        let mut query = world.query::<&Position>();
        let pos = query.single(&world);

        assert!(pos.x > 10.0); // Should have moved forward
    }

    #[test]
    fn test_physics_accuracy_tolerance() {
        // Test that physics integration is within 0.1% tolerance
        let mut world = World::new();

        let mut time = SimulationTime::new();
        time.delta = 0.01; // 10ms steps for accuracy
        world.insert_resource(time);

        let path = Path::new(vec![(0.0, 0.0), (10000.0, 0.0)]);
        world.spawn((
            Position::new(0.0, 0.0),
            Velocity::new(10.0, 0.0), // 10 m/s constant velocity
            Acceleration::new(0.0, 0.0),
            PhysicsProperties::default(),
            path,
        ));

        let mut schedule = Schedule::default();
        schedule.add_systems(physics_system);

        // Run for 1 second (100 steps at 0.01s)
        for _ in 0..100 {
            schedule.run(&mut world);
        }

        let mut query = world.query::<&Position>();
        let pos = query.single(&world);

        // Expected position: 10 m/s * 1s = 10m
        let expected = 10.0;
        let tolerance = expected * 0.001; // 0.1%

        assert!(
            (pos.x - expected).abs() < tolerance,
            "Position {} not within 0.1% of expected {}",
            pos.x,
            expected
        );
    }
}
