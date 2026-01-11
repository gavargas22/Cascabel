//! Benchmarks for WebSocket message serialization
//!
//! Run with: cargo bench --bench websocket_benchmarks
//!
//! These benchmarks verify:
//! - MessagePack is faster than JSON serialization
//! - Message sizes meet targets (< 50% of JSON)
//! - 5000+ car updates can be serialized within latency budget

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

use cascabel_api::messages::{
    CarState, MetricsUpdate, PositionOnlyUpdate, ServerMessage, ServiceNodeState,
    SimulationUpdate,
};

/// Generate test car data for benchmarks
fn generate_car_states(count: usize) -> Vec<CarState> {
    (0..count)
        .map(|i| CarState {
            id: i as u32,
            position: [
                32.5 + (i as f32 * 0.0001),
                -117.0 + (i as f32 * 0.0001),
            ],
            velocity: 10.0 + (i as f32 * 0.01),
            status: (i % 4) as u8,
            queue_id: if i % 2 == 0 { Some(i as u32 % 3) } else { None },
            queue_position: if i % 2 == 0 { Some(i as u32) } else { None },
        })
        .collect()
}

/// Generate a full simulation update
fn generate_simulation_update(car_count: usize) -> SimulationUpdate {
    SimulationUpdate {
        cars: generate_car_states(car_count),
        metrics: MetricsUpdate {
            total_arrivals: car_count as u32,
            total_completions: (car_count / 2) as u32,
            average_wait_time: Some(120.5),
            simulation_time: 3600.0,
        },
        service_nodes: (0..10)
            .map(|i| ServiceNodeState {
                node_id: format!("booth_{}", i),
                queue_id: i % 3,
                is_busy: i % 2 == 0,
                current_car_id: if i % 2 == 0 { Some(i) } else { None },
                service_rate: 3.0,
                total_served: 250,
            })
            .collect(),
        timestamp: 1234567890.123,
    }
}

/// Generate position-only update
fn generate_position_update(car_count: usize) -> PositionOnlyUpdate {
    PositionOnlyUpdate {
        positions: (0..car_count)
            .map(|i| {
                (
                    i as u32,
                    32.5 + (i as f32 * 0.0001),
                    -117.0 + (i as f32 * 0.0001),
                )
            })
            .collect(),
        timestamp: 1234567890.123,
    }
}

/// Benchmark MessagePack serialization vs JSON
fn bench_serialization_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("serialization_comparison");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let update = generate_simulation_update(*car_count);
        let msg = ServerMessage::SimulationUpdate(update);

        group.throughput(Throughput::Elements(*car_count as u64));

        group.bench_with_input(
            BenchmarkId::new("msgpack", car_count),
            &msg,
            |b, msg| {
                b.iter(|| black_box(rmp_serde::to_vec(black_box(msg)).unwrap()));
            },
        );

        group.bench_with_input(
            BenchmarkId::new("json", car_count),
            &msg,
            |b, msg| {
                b.iter(|| black_box(serde_json::to_vec(black_box(msg)).unwrap()));
            },
        );
    }

    group.finish();
}

/// Benchmark deserialization
fn bench_deserialization(c: &mut Criterion) {
    let mut group = c.benchmark_group("deserialization");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let update = generate_simulation_update(*car_count);
        let msg = ServerMessage::SimulationUpdate(update);

        let msgpack_bytes = rmp_serde::to_vec(&msg).unwrap();
        let json_bytes = serde_json::to_vec(&msg).unwrap();

        group.throughput(Throughput::Elements(*car_count as u64));

        group.bench_with_input(
            BenchmarkId::new("msgpack", car_count),
            &msgpack_bytes,
            |b, bytes| {
                b.iter(|| {
                    black_box(rmp_serde::from_slice::<ServerMessage>(black_box(bytes)).unwrap())
                });
            },
        );

        group.bench_with_input(
            BenchmarkId::new("json", car_count),
            &json_bytes,
            |b, bytes| {
                b.iter(|| {
                    black_box(serde_json::from_slice::<ServerMessage>(black_box(bytes)).unwrap())
                });
            },
        );
    }

    group.finish();
}

/// Benchmark position-only updates (high frequency path)
fn bench_position_only(c: &mut Criterion) {
    let mut group = c.benchmark_group("position_only_update");

    for car_count in [100, 500, 1000, 2000, 5000].iter() {
        let update = generate_position_update(*car_count);
        let msg = ServerMessage::PositionOnly(update);

        group.throughput(Throughput::Elements(*car_count as u64));

        group.bench_with_input(
            BenchmarkId::new("serialize", car_count),
            &msg,
            |b, msg| {
                b.iter(|| black_box(rmp_serde::to_vec(black_box(msg)).unwrap()));
            },
        );

        let bytes = rmp_serde::to_vec(&msg).unwrap();
        group.bench_with_input(
            BenchmarkId::new("deserialize", car_count),
            &bytes,
            |b, bytes| {
                b.iter(|| {
                    black_box(rmp_serde::from_slice::<ServerMessage>(black_box(bytes)).unwrap())
                });
            },
        );
    }

    group.finish();
}

/// Benchmark broadcast overhead (serialization + channel send)
fn bench_broadcast_overhead(c: &mut Criterion) {
    use tokio::sync::broadcast;

    let rt = tokio::runtime::Runtime::new().unwrap();
    let mut group = c.benchmark_group("broadcast_overhead");

    for car_count in [100, 1000, 5000].iter() {
        let update = generate_simulation_update(*car_count);
        let msg = ServerMessage::SimulationUpdate(update);

        group.throughput(Throughput::Elements(*car_count as u64));

        group.bench_with_input(
            BenchmarkId::new("serialize_and_send", car_count),
            &msg,
            |b, msg| {
                let (tx, _rx) = broadcast::channel::<Vec<u8>>(100);
                let mut rx = tx.subscribe();

                b.iter(|| {
                    let bytes = rmp_serde::to_vec(black_box(msg)).unwrap();
                    tx.send(bytes).unwrap();
                });

                // Consume messages to prevent buffer overflow
                rt.block_on(async {
                    while rx.try_recv().is_ok() {}
                });
            },
        );
    }

    group.finish();
}

/// Report size comparison
fn report_sizes(c: &mut Criterion) {
    let mut group = c.benchmark_group("size_report");

    for car_count in [100, 500, 1000, 5000].iter() {
        let update = generate_simulation_update(*car_count);
        let msg = ServerMessage::SimulationUpdate(update.clone());

        let msgpack_bytes = rmp_serde::to_vec(&msg).unwrap();
        let json_bytes = serde_json::to_vec(&msg).unwrap();

        let ratio = msgpack_bytes.len() as f64 / json_bytes.len() as f64;
        let savings = 1.0 - ratio;

        println!(
            "{} cars: MessagePack={} bytes, JSON={} bytes, savings={:.1}%",
            car_count,
            msgpack_bytes.len(),
            json_bytes.len(),
            savings * 100.0
        );

        // Position-only comparison
        let pos_update = generate_position_update(*car_count);
        let pos_msg = ServerMessage::PositionOnly(pos_update);
        let pos_bytes = rmp_serde::to_vec(&pos_msg).unwrap();

        let pos_vs_full = pos_bytes.len() as f64 / msgpack_bytes.len() as f64;
        println!(
            "  Position-only: {} bytes ({:.1}% of full update)",
            pos_bytes.len(),
            pos_vs_full * 100.0
        );

        // Just a dummy benchmark to trigger output
        group.throughput(Throughput::Bytes(msgpack_bytes.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("msgpack_size", car_count),
            &msgpack_bytes,
            |b, bytes| {
                b.iter(|| black_box(bytes.len()));
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_serialization_comparison,
    bench_deserialization,
    bench_position_only,
    bench_broadcast_overhead,
    report_sizes,
);

criterion_main!(benches);
