from cascabel.models.waitline import WaitLine
from cascabel.models.simulation import Simulation
from cascabel.models.models import BorderCrossingConfig, SimulationConfig

# Create waitline
waitline = WaitLine(
    geojson_path="cascabel/paths/usa2mx/bota.geojson",
    speed_regime={"slow": 0.8, "fast": 0.2},
    line_length_seed=0.5,
)

# Configure border crossing with multiple queues and service nodes
border_config = BorderCrossingConfig(
    num_queues=3,  # 3 queues/lanes
    nodes_per_queue=[2, 3, 2],  # 2, 3, 2 booths per queue
    arrival_rate=6.0,  # 6 cars per minute total
    service_rates=[3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9],  # Rates per booth
    queue_assignment="shortest",  # Assign to shortest queue
    safe_distance=8.0,  # 8 meters between cars
    max_queue_length=50,
)

# Configure simulation
simulation_config = SimulationConfig(
    max_simulation_time=3600.0,  # 1 hour
    time_factor=1.0,
    enable_telemetry=True,
    enable_position_tracking=True,
)

# Create multi-queue simulation
simulation = Simulation(
    waitline=waitline, border_config=border_config, simulation_config=simulation_config
)

# Run simulation
simulation()

# Print final statistics
stats = simulation.get_statistics()
print("\n=== Border Crossing Simulation Results ===")
print(f"Total simulation time: {stats.simulation_duration:.0f} seconds")
print(f"Total arrivals: {stats.execution_stats.total_arrivals}")
print(f"Total completions: {stats.execution_stats.total_completions}")
print(f"Overall utilization: {stats.execution_stats.overall_utilization:.1%}")
print(f"Positions recorded: {stats.total_positions_recorded}")

print("\nQueue Statistics:")
for queue_stat in stats.queue_stats:
    print(
        f"  Queue {queue_stat.queue_id}: "
        f"{queue_stat.total_cars} cars, "
        f"{queue_stat.busy_nodes}/{queue_stat.num_service_nodes} busy nodes"
    )

print("\nService Node Status:")
for node_stat in stats.node_stats:
    print(
        f"  {node_stat.node_id}: "
        f"rate: {node_stat.service_rate:.1f} cars/min, "
        f"served: {node_stat.total_served}"
    )

# Example position calculation
position = waitline.compute_position_at_distance_from_start(100)
print(f"\nPosition at 100m: {position}")
