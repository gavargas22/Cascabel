//! Spatial Indexing for Collision Detection
//!
//! This module implements R-tree based spatial indexing using the `rstar` crate
//! for efficient O(log n) collision detection instead of O(n^2) brute force.
//!
//! Key components:
//! - `CarSpatialEntry`: A point in the R-tree representing a car's position
//! - `SpatialIndex`: Resource that wraps the R-tree
//! - Systems for updating and querying the spatial index

use bevy_ecs::prelude::*;
use rstar::{PointDistance, RTree, RTreeObject, AABB};

use super::components::{Car, Position};

/// A spatial entry for a car in the R-tree
///
/// Implements RTreeObject to be inserted into an R-tree.
/// Stores the entity and car ID for efficient lookups.
#[derive(Debug, Clone, Copy)]
pub struct CarSpatialEntry {
    /// The ECS entity for this car
    pub entity: Entity,
    /// The car's unique ID
    pub car_id: u32,
    /// The car's position as [x, y]
    pub position: [f64; 2],
    /// The car's length in meters (for collision calculations)
    pub length: f64,
}

impl CarSpatialEntry {
    /// Create a new spatial entry from car data
    pub fn new(entity: Entity, car_id: u32, x: f64, y: f64, length: f64) -> Self {
        Self {
            entity,
            car_id,
            position: [x, y],
            length,
        }
    }

    /// Get the position as a Position component
    pub fn as_position(&self) -> Position {
        Position::new(self.position[0], self.position[1])
    }
}

impl RTreeObject for CarSpatialEntry {
    type Envelope = AABB<[f64; 2]>;

    fn envelope(&self) -> Self::Envelope {
        AABB::from_point(self.position)
    }
}

impl PointDistance for CarSpatialEntry {
    fn distance_2(&self, point: &[f64; 2]) -> f64 {
        let dx = self.position[0] - point[0];
        let dy = self.position[1] - point[1];
        dx * dx + dy * dy
    }
}

/// Spatial index resource wrapping the R-tree
///
/// This resource should be updated every N frames (configurable via rebuild_interval).
/// It provides efficient spatial queries for collision detection.
#[derive(Resource)]
pub struct SpatialIndex {
    /// The R-tree containing all car positions
    tree: RTree<CarSpatialEntry>,
    /// Frame counter for rebuild scheduling
    frame_count: u32,
    /// Rebuild interval (rebuild tree every N frames)
    rebuild_interval: u32,
    /// Whether the tree needs to be rebuilt
    needs_rebuild: bool,
}

impl Default for SpatialIndex {
    fn default() -> Self {
        Self::new()
    }
}

impl SpatialIndex {
    /// Create a new empty spatial index
    pub fn new() -> Self {
        Self {
            tree: RTree::new(),
            frame_count: 0,
            rebuild_interval: 10, // Rebuild every 10 frames
            needs_rebuild: true,
        }
    }

    /// Create a spatial index with custom rebuild interval
    pub fn with_rebuild_interval(interval: u32) -> Self {
        Self {
            tree: RTree::new(),
            frame_count: 0,
            rebuild_interval: interval,
            needs_rebuild: true,
        }
    }

    /// Rebuild the R-tree from a collection of car data
    ///
    /// Uses bulk_load for optimal tree structure (O(n log n)).
    pub fn rebuild(&mut self, entries: Vec<CarSpatialEntry>) {
        self.tree = RTree::bulk_load(entries);
        self.needs_rebuild = false;
    }

    /// Mark the index as needing rebuild
    pub fn mark_dirty(&mut self) {
        self.needs_rebuild = true;
    }

    /// Check if rebuild is needed and increment frame counter
    ///
    /// Returns true if the index should be rebuilt this frame.
    pub fn should_rebuild(&mut self) -> bool {
        self.frame_count = self.frame_count.wrapping_add(1);
        if self.frame_count % self.rebuild_interval == 0 {
            self.needs_rebuild = true;
        }
        self.needs_rebuild
    }

    /// Get the number of entries in the tree
    pub fn len(&self) -> usize {
        self.tree.size()
    }

    /// Check if the tree is empty
    pub fn is_empty(&self) -> bool {
        self.tree.size() == 0
    }

    /// Find all cars within a given distance from a point
    ///
    /// # Arguments
    /// * `point` - The query point [x, y]
    /// * `max_distance` - Maximum distance in meters
    ///
    /// # Returns
    /// Iterator over all cars within the specified distance
    pub fn query_within_distance(
        &self,
        point: [f64; 2],
        max_distance: f64,
    ) -> impl Iterator<Item = &CarSpatialEntry> {
        let max_distance_squared = max_distance * max_distance;
        self.tree
            .locate_within_distance(point, max_distance_squared)
    }

    /// Find all cars within a bounding box
    ///
    /// # Arguments
    /// * `min` - Minimum corner [x, y]
    /// * `max` - Maximum corner [x, y]
    ///
    /// # Returns
    /// Iterator over all cars within the bounding box
    pub fn query_in_envelope(
        &self,
        min: [f64; 2],
        max: [f64; 2],
    ) -> impl Iterator<Item = &CarSpatialEntry> {
        let envelope = AABB::from_corners(min, max);
        self.tree.locate_in_envelope(&envelope)
    }

    /// Find the K nearest neighbors to a point
    ///
    /// # Arguments
    /// * `point` - The query point [x, y]
    /// * `k` - Number of neighbors to find
    ///
    /// # Returns
    /// Vector of up to K nearest cars, sorted by distance
    pub fn query_nearest(&self, point: [f64; 2], k: usize) -> Vec<&CarSpatialEntry> {
        self.tree.nearest_neighbor_iter(&point).take(k).collect()
    }

    /// Find the single nearest neighbor to a point
    pub fn query_nearest_one(&self, point: [f64; 2]) -> Option<&CarSpatialEntry> {
        self.tree.nearest_neighbor(&point)
    }

    /// Find all cars within distance, excluding a specific entity
    ///
    /// Useful for finding cars near a specific car without including itself.
    pub fn query_nearby_excluding(
        &self,
        point: [f64; 2],
        max_distance: f64,
        exclude_entity: Entity,
    ) -> Vec<&CarSpatialEntry> {
        self.query_within_distance(point, max_distance)
            .filter(|entry| entry.entity != exclude_entity)
            .collect()
    }

    /// Get direct access to the R-tree for advanced queries
    pub fn tree(&self) -> &RTree<CarSpatialEntry> {
        &self.tree
    }

    /// Find the closest blocking car ahead of a given car
    ///
    /// A car is "blocking" if it's within detection_range and closer to the booth.
    /// This is the spatial-index-accelerated version of the brute-force approach.
    ///
    /// # Arguments
    /// * `car_entity` - Entity to exclude from search
    /// * `car_position` - Current position of the querying car
    /// * `car_distance_to_booth` - Distance from querying car to booth
    /// * `detection_range` - Maximum distance to search for nearby cars
    /// * `booth_position` - Position of the booth (for calculating relative distances)
    ///
    /// # Returns
    /// Tuple of (gap_distance, car_entry) for the closest blocking car, or None
    pub fn find_blocking_car(
        &self,
        car_entity: Entity,
        car_position: [f64; 2],
        car_distance_to_booth: f64,
        detection_range: f64,
        booth_position: Option<[f64; 2]>,
    ) -> Option<(f64, &CarSpatialEntry)> {
        let nearby = self.query_nearby_excluding(car_position, detection_range, car_entity);

        let mut closest: Option<(f64, &CarSpatialEntry)> = None;

        for entry in nearby {
            // Calculate distance to booth for other car
            let other_distance_to_booth = if let Some(booth) = booth_position {
                let dx = entry.position[0] - booth[0];
                let dy = entry.position[1] - booth[1];
                (dx * dx + dy * dy).sqrt()
            } else {
                // Without booth position, we can't determine if car is ahead
                continue;
            };

            // Calculate geographic distance between cars
            let dx = car_position[0] - entry.position[0];
            let dy = car_position[1] - entry.position[1];
            let geo_distance = (dx * dx + dy * dy).sqrt();

            // Car is "blocking" if it's closer to booth OR very close geographically
            let safe_distance = 3.0; // Could be made configurable
            let is_blocking = other_distance_to_booth < car_distance_to_booth
                || geo_distance < safe_distance * 3.0;

            if is_blocking {
                // Calculate gap (distance minus car length)
                let gap = geo_distance - entry.length;

                // Update closest if this is nearer
                if closest.is_none() || gap < closest.unwrap().0 {
                    closest = Some((gap, entry));
                }
            }
        }

        closest
    }
}

/// System that updates the spatial index with current car positions
///
/// This system rebuilds the R-tree every N frames (configurable).
/// For moving objects like cars, full rebuilds are more efficient than
/// incremental updates because most positions change every frame.
pub fn spatial_index_update_system(
    mut spatial_index: ResMut<SpatialIndex>,
    query: Query<(Entity, &Car, &Position)>,
) {
    if !spatial_index.should_rebuild() {
        return;
    }

    let entries: Vec<CarSpatialEntry> = query
        .iter()
        .map(|(entity, car, pos)| CarSpatialEntry::new(entity, car.id, pos.x, pos.y, car.length))
        .collect();

    spatial_index.rebuild(entries);
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy_ecs::entity::Entity;

    // ========== CarSpatialEntry Tests ==========

    #[test]
    fn test_car_spatial_entry_creation() {
        let entity = Entity::from_raw(1);
        let entry = CarSpatialEntry::new(entity, 42, 100.0, 200.0, 4.5);

        assert_eq!(entry.car_id, 42);
        assert_eq!(entry.position, [100.0, 200.0]);
        assert_eq!(entry.length, 4.5);
        assert_eq!(entry.entity, entity);
    }

    #[test]
    fn test_car_spatial_entry_as_position() {
        let entity = Entity::from_raw(1);
        let entry = CarSpatialEntry::new(entity, 1, 50.0, 75.0, 4.5);

        let pos = entry.as_position();
        assert!((pos.x - 50.0).abs() < 1e-10);
        assert!((pos.y - 75.0).abs() < 1e-10);
    }

    #[test]
    fn test_car_spatial_entry_envelope() {
        let entity = Entity::from_raw(1);
        let entry = CarSpatialEntry::new(entity, 1, 100.0, 200.0, 4.5);

        let envelope = entry.envelope();
        let lower = envelope.lower();
        let upper = envelope.upper();

        assert!((lower[0] - 100.0).abs() < 1e-10);
        assert!((lower[1] - 200.0).abs() < 1e-10);
        assert!((upper[0] - 100.0).abs() < 1e-10);
        assert!((upper[1] - 200.0).abs() < 1e-10);
    }

    #[test]
    fn test_car_spatial_entry_distance() {
        let entity = Entity::from_raw(1);
        let entry = CarSpatialEntry::new(entity, 1, 0.0, 0.0, 4.5);

        // Distance squared to point (3, 4) should be 25
        let dist_sq = entry.distance_2(&[3.0, 4.0]);
        assert!((dist_sq - 25.0).abs() < 1e-10);
    }

    // ========== SpatialIndex Creation Tests ==========

    #[test]
    fn test_spatial_index_creation() {
        let index = SpatialIndex::new();
        assert_eq!(index.len(), 0);
        assert!(index.is_empty());
    }

    #[test]
    fn test_spatial_index_with_custom_interval() {
        let index = SpatialIndex::with_rebuild_interval(5);
        assert_eq!(index.rebuild_interval, 5);
    }

    // ========== R-tree Insertion Tests ==========

    #[test]
    fn test_spatial_index_rebuild_single_entry() {
        let mut index = SpatialIndex::new();
        let entries = vec![CarSpatialEntry::new(
            Entity::from_raw(1),
            1,
            100.0,
            200.0,
            4.5,
        )];

        index.rebuild(entries);

        assert_eq!(index.len(), 1);
        assert!(!index.is_empty());
    }

    #[test]
    fn test_spatial_index_rebuild_multiple_entries() {
        let mut index = SpatialIndex::new();
        let entries: Vec<_> = (0..100)
            .map(|i| {
                CarSpatialEntry::new(
                    Entity::from_raw(i as u32),
                    i as u32,
                    i as f64 * 10.0,
                    i as f64 * 5.0,
                    4.5,
                )
            })
            .collect();

        index.rebuild(entries);

        assert_eq!(index.len(), 100);
    }

    #[test]
    fn test_spatial_index_rebuild_replaces_previous() {
        let mut index = SpatialIndex::new();

        // First build with 10 entries
        let entries1: Vec<_> = (0..10)
            .map(|i| CarSpatialEntry::new(Entity::from_raw(i), i, 0.0, 0.0, 4.5))
            .collect();
        index.rebuild(entries1);
        assert_eq!(index.len(), 10);

        // Rebuild with 5 entries
        let entries2: Vec<_> = (0..5)
            .map(|i| CarSpatialEntry::new(Entity::from_raw(i), i, 0.0, 0.0, 4.5))
            .collect();
        index.rebuild(entries2);
        assert_eq!(index.len(), 5);
    }

    // ========== Nearest Neighbor Tests ==========

    #[test]
    fn test_query_nearest_one() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 10.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 20.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query from (5, 0) - nearest should be car at (0, 0) or (10, 0)
        let nearest = index.query_nearest_one([5.0, 0.0]);
        assert!(nearest.is_some());

        let nearest = nearest.unwrap();
        // Either car 1 at (0,0) or car 2 at (10,0) - both are 5 units away
        assert!(nearest.car_id == 1 || nearest.car_id == 2);
    }

    #[test]
    fn test_query_nearest_one_empty_tree() {
        let index = SpatialIndex::new();
        let nearest = index.query_nearest_one([0.0, 0.0]);
        assert!(nearest.is_none());
    }

    #[test]
    fn test_query_nearest_k() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 5.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 10.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(4), 4, 100.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query 3 nearest from (4, 0)
        let nearest = index.query_nearest([4.0, 0.0], 3);
        assert_eq!(nearest.len(), 3);

        // First should be car 2 (at 5.0, distance = 1)
        assert_eq!(nearest[0].car_id, 2);
        // Second should be car 1 (at 0.0, distance = 4)
        assert_eq!(nearest[1].car_id, 1);
        // Third should be car 3 (at 10.0, distance = 6)
        assert_eq!(nearest[2].car_id, 3);
    }

    #[test]
    fn test_query_nearest_more_than_available() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 10.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Request 10 nearest but only 2 exist
        let nearest = index.query_nearest([0.0, 0.0], 10);
        assert_eq!(nearest.len(), 2);
    }

    // ========== Distance Query Tests ==========

    #[test]
    fn test_query_within_distance() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 5.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 15.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(4), 4, 100.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query within 10m from origin
        let nearby: Vec<_> = index.query_within_distance([0.0, 0.0], 10.0).collect();
        assert_eq!(nearby.len(), 2); // Cars 1 and 2

        let car_ids: Vec<_> = nearby.iter().map(|e| e.car_id).collect();
        assert!(car_ids.contains(&1));
        assert!(car_ids.contains(&2));
    }

    #[test]
    fn test_query_within_distance_none_found() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 100.0, 100.0, 4.5),
        ];
        index.rebuild(entries);

        // Query within 10m from origin - nothing should be found
        let nearby: Vec<_> = index.query_within_distance([0.0, 0.0], 10.0).collect();
        assert_eq!(nearby.len(), 0);
    }

    #[test]
    fn test_query_within_distance_all_found() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 1.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 2.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 3.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query within 100m from origin - all should be found
        let nearby: Vec<_> = index.query_within_distance([0.0, 0.0], 100.0).collect();
        assert_eq!(nearby.len(), 3);
    }

    #[test]
    fn test_query_nearby_excluding() {
        let mut index = SpatialIndex::new();
        let entity_to_exclude = Entity::from_raw(2);
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_to_exclude, 2, 5.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 8.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query within 10m from (5, 0), excluding entity 2
        let nearby = index.query_nearby_excluding([5.0, 0.0], 10.0, entity_to_exclude);
        assert_eq!(nearby.len(), 2);

        // Should not include car 2
        for entry in &nearby {
            assert_ne!(entry.entity, entity_to_exclude);
        }
    }

    // ========== Bounding Box Query Tests ==========

    #[test]
    fn test_query_in_envelope() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(2), 2, 50.0, 50.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(3), 3, 100.0, 100.0, 4.5),
            CarSpatialEntry::new(Entity::from_raw(4), 4, 200.0, 200.0, 4.5),
        ];
        index.rebuild(entries);

        // Query bounding box from (25, 25) to (150, 150)
        let in_box: Vec<_> = index.query_in_envelope([25.0, 25.0], [150.0, 150.0]).collect();
        assert_eq!(in_box.len(), 2); // Cars 2 and 3

        let car_ids: Vec<_> = in_box.iter().map(|e| e.car_id).collect();
        assert!(car_ids.contains(&2));
        assert!(car_ids.contains(&3));
    }

    #[test]
    fn test_query_in_envelope_empty() {
        let mut index = SpatialIndex::new();
        let entries = vec![
            CarSpatialEntry::new(Entity::from_raw(1), 1, 0.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Query bounding box that doesn't contain any cars
        let in_box: Vec<_> = index.query_in_envelope([100.0, 100.0], [200.0, 200.0]).collect();
        assert_eq!(in_box.len(), 0);
    }

    // ========== Rebuild Strategy Tests ==========

    #[test]
    fn test_should_rebuild_interval() {
        let mut index = SpatialIndex::with_rebuild_interval(3);

        // Initial state: needs_rebuild is true
        assert!(index.needs_rebuild);

        // Frame 1: should rebuild (initial needs_rebuild is true)
        assert!(index.should_rebuild());
        index.rebuild(vec![]); // Reset needs_rebuild

        // Frame 2: frame_count = 2, 2 % 3 != 0, needs_rebuild = false
        assert!(!index.should_rebuild());

        // Frame 3: frame_count = 3, 3 % 3 == 0, needs_rebuild = true
        assert!(index.should_rebuild());
        index.rebuild(vec![]); // Reset

        // Frame 4: frame_count = 4, 4 % 3 != 0, needs_rebuild = false
        assert!(!index.should_rebuild());

        // Frame 5: frame_count = 5, 5 % 3 != 0, needs_rebuild = false
        assert!(!index.should_rebuild());

        // Frame 6: frame_count = 6, 6 % 3 == 0, needs_rebuild = true
        assert!(index.should_rebuild());
    }

    #[test]
    fn test_mark_dirty() {
        let mut index = SpatialIndex::with_rebuild_interval(100);
        index.rebuild(vec![]);

        // Should not need rebuild right after rebuild
        assert!(!index.needs_rebuild);

        // Mark as dirty
        index.mark_dirty();
        assert!(index.needs_rebuild);
    }

    // ========== System Tests ==========

    #[test]
    fn test_spatial_index_update_system() {
        use bevy_ecs::world::World;

        let mut world = World::new();
        world.insert_resource(SpatialIndex::new());

        // Spawn some cars
        for i in 0..10 {
            world.spawn((
                Car::new(i),
                Position::new(i as f64 * 10.0, i as f64 * 5.0),
            ));
        }

        // Run the update system
        let mut schedule = bevy_ecs::schedule::Schedule::default();
        schedule.add_systems(spatial_index_update_system);
        schedule.run(&mut world);

        // Check that spatial index was populated
        let index = world.resource::<SpatialIndex>();
        assert_eq!(index.len(), 10);
    }

    #[test]
    fn test_spatial_index_update_system_respects_interval() {
        use bevy_ecs::world::World;

        let mut world = World::new();
        world.insert_resource(SpatialIndex::with_rebuild_interval(5));

        // Spawn a car
        world.spawn((Car::new(1), Position::new(100.0, 200.0)));

        // First run - should rebuild
        let mut schedule = bevy_ecs::schedule::Schedule::default();
        schedule.add_systems(spatial_index_update_system);
        schedule.run(&mut world);

        let index = world.resource::<SpatialIndex>();
        assert_eq!(index.len(), 1);

        // Add another car
        world.spawn((Car::new(2), Position::new(300.0, 400.0)));

        // Second run - should NOT rebuild (interval = 5)
        schedule.run(&mut world);

        // Index should still have 1 entry (not rebuilt)
        let index = world.resource::<SpatialIndex>();
        assert_eq!(index.len(), 1);
    }

    // ========== Collision Detection Tests ==========

    #[test]
    fn test_find_blocking_car_none_ahead() {
        let mut index = SpatialIndex::new();
        let entity_self = Entity::from_raw(1);
        let entity_behind = Entity::from_raw(2);

        // Booth is at (100, 0)
        // Self car is at (50, 0) - closer to booth
        // Other car is at (0, 0) - further from booth
        let entries = vec![
            CarSpatialEntry::new(entity_self, 1, 50.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_behind, 2, 0.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        let booth = Some([100.0, 0.0]);
        let result = index.find_blocking_car(
            entity_self,
            [50.0, 0.0],
            50.0, // distance to booth
            30.0, // detection range
            booth,
        );

        // Car behind should not be blocking
        assert!(result.is_none());
    }

    #[test]
    fn test_find_blocking_car_one_ahead() {
        let mut index = SpatialIndex::new();
        let entity_self = Entity::from_raw(1);
        let entity_ahead = Entity::from_raw(2);

        // Booth is at (100, 0)
        // Self car is at (50, 0) - 50m from booth
        // Other car is at (70, 0) - 30m from booth (closer = ahead)
        let entries = vec![
            CarSpatialEntry::new(entity_self, 1, 50.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_ahead, 2, 70.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        let booth = Some([100.0, 0.0]);
        let result = index.find_blocking_car(
            entity_self,
            [50.0, 0.0],
            50.0, // distance to booth
            30.0, // detection range
            booth,
        );

        assert!(result.is_some());
        let (gap, blocking_car) = result.unwrap();
        assert_eq!(blocking_car.car_id, 2);
        // Gap should be distance (20m) minus car length (4.5m) = 15.5m
        assert!((gap - 15.5).abs() < 0.01);
    }

    #[test]
    fn test_find_blocking_car_closest_when_multiple() {
        let mut index = SpatialIndex::new();
        let entity_self = Entity::from_raw(1);
        let entity_near = Entity::from_raw(2);
        let entity_far = Entity::from_raw(3);

        // Booth is at (100, 0)
        // Self car is at (20, 0)
        // Near car is at (30, 0) - 10m away
        // Far car is at (60, 0) - 40m away
        let entries = vec![
            CarSpatialEntry::new(entity_self, 1, 20.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_near, 2, 30.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_far, 3, 60.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        let booth = Some([100.0, 0.0]);
        let result = index.find_blocking_car(
            entity_self,
            [20.0, 0.0],
            80.0, // distance to booth
            50.0, // detection range
            booth,
        );

        assert!(result.is_some());
        let (gap, blocking_car) = result.unwrap();
        // Should find the nearer car
        assert_eq!(blocking_car.car_id, 2);
        // Gap should be 10m - 4.5m = 5.5m
        assert!((gap - 5.5).abs() < 0.01);
    }

    #[test]
    fn test_find_blocking_car_outside_detection_range() {
        let mut index = SpatialIndex::new();
        let entity_self = Entity::from_raw(1);
        let entity_ahead = Entity::from_raw(2);

        // Booth is at (100, 0)
        // Self car is at (0, 0)
        // Other car is at (80, 0) - ahead but 80m away, outside 30m detection range
        let entries = vec![
            CarSpatialEntry::new(entity_self, 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_ahead, 2, 80.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        let booth = Some([100.0, 0.0]);
        let result = index.find_blocking_car(
            entity_self,
            [0.0, 0.0],
            100.0, // distance to booth
            30.0,  // detection range - car at 80m is outside
            booth,
        );

        assert!(result.is_none());
    }

    #[test]
    fn test_find_blocking_car_no_booth() {
        let mut index = SpatialIndex::new();
        let entity_self = Entity::from_raw(1);
        let entity_other = Entity::from_raw(2);

        let entries = vec![
            CarSpatialEntry::new(entity_self, 1, 0.0, 0.0, 4.5),
            CarSpatialEntry::new(entity_other, 2, 10.0, 0.0, 4.5),
        ];
        index.rebuild(entries);

        // Without booth position, can't determine blocking
        let result = index.find_blocking_car(
            entity_self,
            [0.0, 0.0],
            100.0,
            30.0,
            None, // No booth
        );

        assert!(result.is_none());
    }

    // ========== Performance Comparison Tests ==========

    /// Helper function for brute-force collision detection (O(n^2))
    fn brute_force_find_nearby(
        entries: &[CarSpatialEntry],
        query_entity: Entity,
        query_pos: [f64; 2],
        detection_range: f64,
    ) -> Vec<&CarSpatialEntry> {
        let max_dist_sq = detection_range * detection_range;
        entries
            .iter()
            .filter(|e| {
                if e.entity == query_entity {
                    return false;
                }
                let dx = e.position[0] - query_pos[0];
                let dy = e.position[1] - query_pos[1];
                dx * dx + dy * dy <= max_dist_sq
            })
            .collect()
    }

    #[test]
    fn test_rtree_matches_brute_force() {
        // Generate test data
        let entries: Vec<_> = (0..100)
            .map(|i| {
                CarSpatialEntry::new(
                    Entity::from_raw(i as u32),
                    i as u32,
                    (i as f64 * 7.0) % 500.0,
                    (i as f64 * 11.0) % 500.0,
                    4.5,
                )
            })
            .collect();

        let mut index = SpatialIndex::new();
        index.rebuild(entries.clone());

        // Query from a random position
        let query_entity = Entity::from_raw(50);
        let query_pos = [200.0, 200.0];
        let detection_range = 50.0;

        // Get results from both methods
        let rtree_results = index.query_nearby_excluding(query_pos, detection_range, query_entity);
        let brute_results =
            brute_force_find_nearby(&entries, query_entity, query_pos, detection_range);

        // Should have same count
        assert_eq!(
            rtree_results.len(),
            brute_results.len(),
            "R-tree and brute force should find same number of results"
        );

        // Should contain same car IDs
        let rtree_ids: std::collections::HashSet<_> =
            rtree_results.iter().map(|e| e.car_id).collect();
        let brute_ids: std::collections::HashSet<_> =
            brute_results.iter().map(|e| e.car_id).collect();
        assert_eq!(rtree_ids, brute_ids);
    }

    #[test]
    fn test_rtree_performance_with_many_cars() {
        use std::time::Instant;

        let car_count = 5000;
        let query_count = 100;

        // Generate test data - cars distributed in a 1km x 1km area
        let entries: Vec<_> = (0..car_count)
            .map(|i| {
                CarSpatialEntry::new(
                    Entity::from_raw(i as u32),
                    i as u32,
                    (i as f64 * 17.0) % 1000.0,
                    (i as f64 * 23.0) % 1000.0,
                    4.5,
                )
            })
            .collect();

        let mut index = SpatialIndex::new();

        // Measure rebuild time
        let rebuild_start = Instant::now();
        index.rebuild(entries.clone());
        let rebuild_time = rebuild_start.elapsed();

        // Measure query time for R-tree
        let rtree_start = Instant::now();
        for i in 0..query_count {
            let query_pos = [(i as f64 * 31.0) % 1000.0, (i as f64 * 37.0) % 1000.0];
            let query_entity = Entity::from_raw((i % car_count) as u32);
            let _results = index.query_nearby_excluding(query_pos, 30.0, query_entity);
        }
        let rtree_time = rtree_start.elapsed();

        // Measure query time for brute force
        let brute_start = Instant::now();
        for i in 0..query_count {
            let query_pos = [(i as f64 * 31.0) % 1000.0, (i as f64 * 37.0) % 1000.0];
            let query_entity = Entity::from_raw((i % car_count) as u32);
            let _results = brute_force_find_nearby(&entries, query_entity, query_pos, 30.0);
        }
        let brute_time = brute_start.elapsed();

        // Print timing (visible in test output with --nocapture)
        println!("Performance with {} cars, {} queries:", car_count, query_count);
        println!("  R-tree rebuild: {:?}", rebuild_time);
        println!("  R-tree queries: {:?}", rtree_time);
        println!("  Brute force queries: {:?}", brute_time);
        println!(
            "  Speedup: {:.1}x",
            brute_time.as_nanos() as f64 / rtree_time.as_nanos() as f64
        );

        // R-tree should be faster for this many cars
        assert!(
            rtree_time < brute_time,
            "R-tree should be faster than brute force with {} cars",
            car_count
        );
    }
}
