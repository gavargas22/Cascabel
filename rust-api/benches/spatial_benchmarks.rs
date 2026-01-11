//! Benchmarks comparing R-tree spatial indexing vs brute force collision detection
//!
//! Run with: cargo bench --bench spatial_benchmarks
//!
//! These benchmarks verify O(log n) query performance for R-tree vs O(n) brute force.

use bevy_ecs::entity::Entity;
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

use cascabel_api::simulation::{CarSpatialEntry, SpatialIndex};

/// Generate test car data for benchmarks
fn generate_car_entries(count: usize) -> Vec<CarSpatialEntry> {
    (0..count)
        .map(|i| {
            CarSpatialEntry::new(
                Entity::from_raw(i as u32),
                i as u32,
                // Distribute cars in a 1km x 1km area
                (i as f64 * 17.0) % 1000.0,
                (i as f64 * 23.0) % 1000.0,
                4.5,
            )
        })
        .collect()
}

/// Brute-force collision detection (O(n) per query)
fn brute_force_query(
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

/// Benchmark R-tree rebuild (bulk_load)
fn bench_rtree_rebuild(c: &mut Criterion) {
    let mut group = c.benchmark_group("rtree_rebuild");

    for size in [100, 500, 1000, 2000, 5000].iter() {
        let entries = generate_car_entries(*size);

        group.throughput(Throughput::Elements(*size as u64));
        group.bench_with_input(BenchmarkId::new("bulk_load", size), &entries, |b, entries| {
            b.iter(|| {
                let mut index = SpatialIndex::new();
                index.rebuild(black_box(entries.clone()));
                index
            });
        });
    }

    group.finish();
}

/// Benchmark R-tree single query vs brute force
fn bench_single_query(c: &mut Criterion) {
    let mut group = c.benchmark_group("single_query");

    for size in [100, 500, 1000, 2000, 5000].iter() {
        let entries = generate_car_entries(*size);
        let mut index = SpatialIndex::new();
        index.rebuild(entries.clone());

        let query_pos = [500.0, 500.0]; // Center of the area
        let query_entity = Entity::from_raw(0);
        let detection_range = 30.0;

        group.bench_with_input(BenchmarkId::new("rtree", size), &index, |b, index| {
            b.iter(|| {
                black_box(index.query_nearby_excluding(
                    black_box(query_pos),
                    black_box(detection_range),
                    black_box(query_entity),
                ))
            });
        });

        group.bench_with_input(BenchmarkId::new("brute_force", size), &entries, |b, entries| {
            b.iter(|| {
                black_box(brute_force_query(
                    black_box(entries),
                    black_box(query_entity),
                    black_box(query_pos),
                    black_box(detection_range),
                ))
            });
        });
    }

    group.finish();
}

/// Benchmark multiple queries per frame (simulating N cars each checking for collisions)
fn bench_multi_query(c: &mut Criterion) {
    let mut group = c.benchmark_group("multi_query_per_frame");

    for size in [100, 500, 1000, 2000, 5000].iter() {
        let entries = generate_car_entries(*size);
        let mut index = SpatialIndex::new();
        index.rebuild(entries.clone());

        let query_count = 100; // 100 cars checking for collisions
        let detection_range = 30.0;

        // Generate query positions
        let query_positions: Vec<_> = (0..query_count)
            .map(|i| {
                let entity = Entity::from_raw((i % *size) as u32);
                let pos = [
                    (i as f64 * 31.0) % 1000.0,
                    (i as f64 * 37.0) % 1000.0,
                ];
                (entity, pos)
            })
            .collect();

        group.throughput(Throughput::Elements(query_count as u64));

        group.bench_with_input(
            BenchmarkId::new("rtree", size),
            &(&index, &query_positions),
            |b, (index, positions)| {
                b.iter(|| {
                    for (entity, pos) in positions.iter() {
                        black_box(index.query_nearby_excluding(
                            black_box(*pos),
                            black_box(detection_range),
                            black_box(*entity),
                        ));
                    }
                });
            },
        );

        group.bench_with_input(
            BenchmarkId::new("brute_force", size),
            &(&entries, &query_positions),
            |b, (entries, positions)| {
                b.iter(|| {
                    for (entity, pos) in positions.iter() {
                        black_box(brute_force_query(
                            black_box(entries),
                            black_box(*entity),
                            black_box(*pos),
                            black_box(detection_range),
                        ));
                    }
                });
            },
        );
    }

    group.finish();
}

/// Benchmark full simulation frame: rebuild + all queries
fn bench_full_frame(c: &mut Criterion) {
    let mut group = c.benchmark_group("full_frame");
    group.sample_size(50); // Fewer samples for longer-running benchmarks

    for size in [1000, 2000, 5000].iter() {
        let entries = generate_car_entries(*size);
        let detection_range = 30.0;

        // Each car queries for nearby cars
        let query_positions: Vec<_> = entries
            .iter()
            .map(|e| (e.entity, e.position))
            .collect();

        group.throughput(Throughput::Elements(*size as u64));

        group.bench_with_input(
            BenchmarkId::new("rtree_with_rebuild", size),
            &(&entries, &query_positions),
            |b, (entries, positions)| {
                b.iter(|| {
                    // Rebuild tree (done every N frames)
                    let mut index = SpatialIndex::new();
                    index.rebuild(black_box(entries.to_vec()));

                    // Each car queries for neighbors
                    for (entity, pos) in positions.iter() {
                        black_box(index.query_nearby_excluding(
                            black_box(*pos),
                            black_box(detection_range),
                            black_box(*entity),
                        ));
                    }
                });
            },
        );

        group.bench_with_input(
            BenchmarkId::new("brute_force", size),
            &(&entries, &query_positions),
            |b, (entries, positions)| {
                b.iter(|| {
                    // Brute force: each car checks all other cars
                    for (entity, pos) in positions.iter() {
                        black_box(brute_force_query(
                            black_box(entries),
                            black_box(*entity),
                            black_box(*pos),
                            black_box(detection_range),
                        ));
                    }
                });
            },
        );
    }

    group.finish();
}

/// Benchmark nearest neighbor queries
fn bench_nearest_neighbor(c: &mut Criterion) {
    let mut group = c.benchmark_group("nearest_neighbor");

    for size in [100, 500, 1000, 5000].iter() {
        let entries = generate_car_entries(*size);
        let mut index = SpatialIndex::new();
        index.rebuild(entries.clone());

        let query_pos = [500.0, 500.0];

        group.bench_with_input(BenchmarkId::new("nearest_1", size), &index, |b, index| {
            b.iter(|| black_box(index.query_nearest_one(black_box(query_pos))));
        });

        group.bench_with_input(BenchmarkId::new("nearest_5", size), &index, |b, index| {
            b.iter(|| black_box(index.query_nearest(black_box(query_pos), 5)));
        });

        group.bench_with_input(BenchmarkId::new("nearest_10", size), &index, |b, index| {
            b.iter(|| black_box(index.query_nearest(black_box(query_pos), 10)));
        });
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_rtree_rebuild,
    bench_single_query,
    bench_multi_query,
    bench_full_frame,
    bench_nearest_neighbor,
);

criterion_main!(benches);
