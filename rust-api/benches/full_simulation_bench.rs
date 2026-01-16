//! Full simulation benchmarks using Criterion
//!
//! Run with: cargo bench --bench full_simulation_bench
//!
//! These benchmarks measure end-to-end simulation performance including:
//! - Physics simulation with various car counts
//! - State extraction for WebSocket broadcasting
//! - Combined simulation + serialization throughput
//! - Memory allocation patterns

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};

use cascabel_api::messages::{
    CarState, MetricsUpdate, PositionOnlyUpdate, ServerMessage, SimulationUpdate,
};
use cascabel_api::simulation::{Path, SimulationConfig, SimulationEngine};

/// Create a simulation engine with specified number of cars
fn create_engine_with_cars(car_count: usize) -> SimulationEngine {
    let mut engine = SimulationEngine::with_config(SimulationConfig {
        safe_distance: 4.0,
        num_queues: 10,
        ..Default::default()
    });

    for i in 0..car_count {
        let lane = (i % 10) as f64 * 10.0;
        let start_x = (i / 10) as f64 * 2.0;
        let path = Path::new(vec![(start_x, lane), (10000.0, lane)]);
        engine.spawn_car(path, (i % 10) as u32);
    }

    engine
}

/// Benchmark physics simulation step with varying car counts
fn bench_physics_step(c: &mut Criterion) {
    let mut group = c.benchmark_group("physics_step");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("step", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    engine.step(black_box(0.01));
                });
            },
        );
    }

    group.finish();
}

/// Benchmark multiple physics steps (simulating 100ms at 100Hz)
fn bench_physics_100ms(c: &mut Criterion) {
    let mut group = c.benchmark_group("physics_100ms");

    for car_count in [100, 1000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        group.throughput(Throughput::Elements(*car_count as u64 * 10));
        group.bench_with_input(
            BenchmarkId::new("10_steps", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    for _ in 0..10 {
                        engine.step(black_box(0.01));
                    }
                });
            },
        );
    }

    group.finish();
}

/// Benchmark state extraction for WebSocket broadcasting
fn bench_get_car_states(c: &mut Criterion) {
    let mut group = c.benchmark_group("get_car_states");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        // Run a few steps to have some state
        for _ in 0..10 {
            engine.step(0.01);
        }

        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("extract", car_count),
            car_count,
            |b, _| {
                b.iter(|| black_box(engine.get_car_states()));
            },
        );
    }

    group.finish();
}

/// Benchmark position-only updates (compact format)
fn bench_get_position_updates(c: &mut Criterion) {
    let mut group = c.benchmark_group("get_position_updates");

    for car_count in [100, 1000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        for _ in 0..10 {
            engine.step(0.01);
        }

        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("extract", car_count),
            car_count,
            |b, _| {
                b.iter(|| black_box(engine.get_position_updates()));
            },
        );
    }

    group.finish();
}

/// Benchmark full update cycle: physics + extraction + serialization
fn bench_full_update_cycle(c: &mut Criterion) {
    let mut group = c.benchmark_group("full_update_cycle");
    group.sample_size(50); // Fewer samples for longer benchmarks

    for car_count in [100, 1000, 2000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("10Hz_update", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    // 10 physics steps (100ms at 100Hz)
                    for _ in 0..10 {
                        engine.step(0.01);
                    }

                    // Extract states
                    let states = engine.get_car_states();
                    let stats = engine.stats();

                    // Create update message
                    let update = SimulationUpdate {
                        cars: states
                            .iter()
                            .map(|s| CarState {
                                id: s.id,
                                position: [s.x as f32, s.y as f32],
                                velocity: s.velocity as f32,
                                status: s.status as u8,
                                queue_id: None,
                                queue_position: None,
                            })
                            .collect(),
                        metrics: MetricsUpdate {
                            total_arrivals: stats.total_arrivals,
                            total_completions: stats.total_completions,
                            average_wait_time: Some(stats.average_wait_time),
                            simulation_time: engine.current_time(),
                        },
                        service_nodes: vec![],
                        timestamp: 0.0,
                    };

                    // Serialize to MessagePack
                    let msg = ServerMessage::SimulationUpdate(update);
                    black_box(rmp_serde::to_vec(&msg).unwrap())
                });
            },
        );
    }

    group.finish();
}

/// Benchmark position-only update cycle (30Hz path)
fn bench_position_only_cycle(c: &mut Criterion) {
    let mut group = c.benchmark_group("position_only_cycle");

    for car_count in [100, 1000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("30Hz_update", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    // 3 physics steps (~33ms at 100Hz for 30Hz update rate)
                    for _ in 0..3 {
                        engine.step(0.01);
                    }

                    // Extract positions
                    let positions = engine.get_position_updates();

                    // Create position-only update
                    let update = PositionOnlyUpdate {
                        positions: positions
                            .iter()
                            .map(|p| (p.id, p.x as f32, p.y as f32))
                            .collect(),
                        timestamp: 0.0,
                    };

                    // Serialize
                    let msg = ServerMessage::PositionOnly(update);
                    black_box(rmp_serde::to_vec(&msg).unwrap())
                });
            },
        );
    }

    group.finish();
}

/// Benchmark car spawning
fn bench_car_spawning(c: &mut Criterion) {
    let mut group = c.benchmark_group("car_spawning");

    group.bench_function("spawn_single", |b| {
        let mut engine = SimulationEngine::new();
        let mut count = 0u32;

        b.iter(|| {
            let path = Path::new(vec![(0.0, (count % 10) as f64 * 10.0), (1000.0, 0.0)]);
            engine.spawn_car(black_box(path), count % 10);
            count += 1;
        });
    });

    for car_count in [100, 1000, 5000].iter() {
        group.throughput(Throughput::Elements(*car_count as u64));
        group.bench_with_input(
            BenchmarkId::new("spawn_batch", car_count),
            car_count,
            |b, &count| {
                b.iter(|| {
                    let mut engine = SimulationEngine::new();
                    for i in 0..count {
                        let path = Path::new(vec![
                            (0.0, (i % 10) as f64 * 10.0),
                            (1000.0, (i % 10) as f64 * 10.0),
                        ]);
                        engine.spawn_car(black_box(path), (i % 10) as u32);
                    }
                    black_box(engine)
                });
            },
        );
    }

    group.finish();
}

/// Benchmark spatial index operations
fn bench_spatial_index(c: &mut Criterion) {
    let mut group = c.benchmark_group("spatial_index_impact");
    group.sample_size(50);

    for car_count in [1000, 2000, 5000].iter() {
        // With spatial indexing
        let mut engine_spatial = create_engine_with_cars(*car_count);
        engine_spatial.set_use_spatial_index(true);

        group.bench_with_input(
            BenchmarkId::new("with_spatial", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    for _ in 0..10 {
                        engine_spatial.step(0.01);
                    }
                });
            },
        );

        // Without spatial indexing
        let mut engine_brute = create_engine_with_cars(*car_count);
        engine_brute.set_use_spatial_index(false);

        group.bench_with_input(
            BenchmarkId::new("brute_force", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    for _ in 0..10 {
                        engine_brute.step(0.01);
                    }
                });
            },
        );
    }

    group.finish();
}

/// Benchmark time scaling impact
fn bench_time_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("time_scaling");

    let mut engine = create_engine_with_cars(1000);

    for scale in [0.5, 1.0, 2.0, 5.0, 10.0].iter() {
        engine.set_time_scale(*scale);

        group.bench_with_input(
            BenchmarkId::new("scale", format!("{:.1}x", scale)),
            scale,
            |b, _| {
                b.iter(|| {
                    engine.step(black_box(0.01));
                });
            },
        );
    }

    group.finish();
}

/// Report message sizes
fn bench_message_sizes(c: &mut Criterion) {
    let mut group = c.benchmark_group("message_sizes");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let update = SimulationUpdate {
            cars: (0..*car_count)
                .map(|i| CarState {
                    id: i,
                    position: [32.5 + (i as f32 * 0.0001), -117.0 + (i as f32 * 0.0001)],
                    velocity: 10.0,
                    status: (i % 4) as u8,
                    queue_id: if i % 2 == 0 { Some(i % 3) } else { None },
                    queue_position: if i % 2 == 0 { Some(i) } else { None },
                })
                .collect(),
            metrics: MetricsUpdate {
                total_arrivals: *car_count,
                total_completions: *car_count / 2,
                average_wait_time: Some(120.0),
                simulation_time: 3600.0,
            },
            service_nodes: vec![],
            timestamp: 0.0,
        };

        let msg = ServerMessage::SimulationUpdate(update);
        let bytes = rmp_serde::to_vec(&msg).unwrap();

        println!(
            "{} cars: {} bytes ({:.2} KB, {:.1} bytes/car)",
            car_count,
            bytes.len(),
            bytes.len() as f64 / 1024.0,
            bytes.len() as f64 / *car_count as f64
        );

        group.throughput(Throughput::Bytes(bytes.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("serialize", car_count),
            &msg,
            |b, msg| {
                b.iter(|| black_box(rmp_serde::to_vec(black_box(msg)).unwrap()));
            },
        );
    }

    group.finish();
}

/// Benchmark sustained throughput (simulating 1 second of updates)
fn bench_sustained_throughput(c: &mut Criterion) {
    let mut group = c.benchmark_group("sustained_throughput");
    group.sample_size(20);
    group.measurement_time(std::time::Duration::from_secs(10));

    for car_count in [1000, 2000, 5000].iter() {
        let mut engine = create_engine_with_cars(*car_count);

        group.throughput(Throughput::Elements(*car_count as u64 * 10)); // 10 updates = 1 sec
        group.bench_with_input(
            BenchmarkId::new("1_second", car_count),
            car_count,
            |b, _| {
                b.iter(|| {
                    // Simulate 1 second: 10 update cycles at 10Hz
                    for _ in 0..10 {
                        // Physics (10 steps at 100Hz = 100ms)
                        for _ in 0..10 {
                            engine.step(0.01);
                        }

                        // Extract and serialize
                        let states = engine.get_car_states();
                        let update = SimulationUpdate {
                            cars: states
                                .iter()
                                .map(|s| CarState {
                                    id: s.id,
                                    position: [s.x as f32, s.y as f32],
                                    velocity: s.velocity as f32,
                                    status: s.status as u8,
                                    queue_id: None,
                                    queue_position: None,
                                })
                                .collect(),
                            metrics: MetricsUpdate {
                                total_arrivals: 0,
                                total_completions: 0,
                                average_wait_time: None,
                                simulation_time: engine.current_time(),
                            },
                            service_nodes: vec![],
                            timestamp: 0.0,
                        };

                        let msg = ServerMessage::SimulationUpdate(update);
                        black_box(rmp_serde::to_vec(&msg).unwrap());
                    }
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_physics_step,
    bench_physics_100ms,
    bench_get_car_states,
    bench_get_position_updates,
    bench_full_update_cycle,
    bench_position_only_cycle,
    bench_car_spawning,
    bench_spatial_index,
    bench_time_scaling,
    bench_message_sizes,
    bench_sustained_throughput,
);

criterion_main!(benches);
