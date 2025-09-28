from shapely.geometry import MultiPoint
import geopandas as gpd
from datetime import datetime, timedelta
from .border_crossing import BorderCrossing
from .models import (
    SimulationConfig,
    BorderCrossingConfig,
    SimulationResult,
    BorderCrossingStats,
    QueueStats,
    ServiceNodeStats,
)


class Simulation:
    """
    Simulation Model
    ----------------

    Multi-queue, multi-service-node border crossing simulation.
    """

    def __init__(
        self, waitline, border_config, simulation_config=None, phone_config=None
    ):
        """
        Initialize simulation.

        Args:
            waitline: WaitLine object defining the path
            border_config: BorderCrossingConfig object
            simulation_config: SimulationConfig object (optional)
            phone_config: PhoneConfig object for telemetry (optional)
        """
        self.waitline = waitline
        self.total_distance = self.waitline.destiny["line_length"]
        self.phone_config = phone_config
        self.start_time = datetime.now()  # Record when simulation starts

        # Use Pydantic models for configuration
        if isinstance(border_config, dict):
            self.border_config = BorderCrossingConfig(**border_config)
        else:
            self.border_config = border_config

        if simulation_config is None:
            self.simulation_config = SimulationConfig(
                max_simulation_time=86400.0,
                time_factor=1.0,
                enable_telemetry=True,
                enable_position_tracking=True,
            )
        elif isinstance(simulation_config, dict):
            self.simulation_config = SimulationConfig(**simulation_config)
        else:
            self.simulation_config = simulation_config

        # Initialize border crossing with multiple queues and service nodes
        self.border_crossing = BorderCrossing(
            waitline, self.border_config, self.phone_config
        )

        self.location_points = []

        # Use simulation config values
        self.simulation_state = {
            "running": False,
            "time_factor": self.simulation_config.time_factor,
            "max_simulation_time": self.simulation_config.max_simulation_time,
        }

        self.temporal_state = {
            "previous_simulation_time": 0,
            "simulation_time": 0,
        }

    def __call__(self):
        print("executing multi-queue border crossing simulation...")
        self.simulation_state["running"] = True

        while self.simulation_state["running"]:
            # Advance time one incremental unit
            dt = self.advance_time()

            # Update border crossing dynamics
            self.border_crossing.advance_time(dt)

            # Check if simulation should continue
            if not self.should_continue():
                self.simulation_state["running"] = False

            # Record car positions for visualization
            self.record_positions()

        stats = self.get_statistics()
        print(f"Simulation completed. Final statistics: {stats}")

    def advance_time(self):
        """
        Advance simulation time and return time delta.
        """
        delta_t_amount = self.simulation_state["time_factor"]
        self.temporal_state["simulation_time"] += delta_t_amount
        return delta_t_amount

    def should_continue(self):
        """
        Determine if simulation should continue.
        """
        # Continue if under max time and have activity
        time_check = (
            self.temporal_state["simulation_time"]
            < self.simulation_state["max_simulation_time"]
        )

        # Continue if there are cars in system or recent arrivals
        total_cars = sum(len(queue.cars) for queue in self.border_crossing.queues)
        activity_check = total_cars > 0 or self.temporal_state["simulation_time"] < 300

        return time_check and activity_check

    def record_positions(self):
        """
        Record current positions and collect telemetry.
        """
        current_time = self.temporal_state["simulation_time"]
        current_datetime = self.start_time + timedelta(seconds=current_time)

        for queue in self.border_crossing.queues:
            for car in queue.cars.values():
                # Get GPS position along waitline
                position_point = self.waitline.compute_position_at_distance_from_start(
                    car.position
                )
                if position_point:
                    self.location_points.append(position_point)

                # Generate telemetry data for this car
                if car.telemetry_gen:
                    telemetry_record = car.generate_telemetry(current_datetime)
                    if telemetry_record:
                        # Store telemetry data (will be collected by API)
                        if not hasattr(self, "telemetry_data"):
                            self.telemetry_data = []
                        self.telemetry_data.append(telemetry_record)

    def get_statistics(self):
        """
        Get comprehensive simulation statistics as Pydantic model.

        Returns:
            SimulationResult: Complete simulation results
        """
        border_stats, queue_stats, node_stats = self.border_crossing.get_statistics()

        return SimulationResult(
            simulation_config=self.simulation_config,
            border_config=self.border_config,
            execution_stats=border_stats,
            queue_stats=queue_stats,
            node_stats=node_stats,
            total_positions_recorded=len(self.location_points),
            total_telemetry_records=0,  # TODO: implement telemetry tracking
            simulation_duration=self.temporal_state["simulation_time"],
        )

    def generate_point_geojson(self):
        """
        Generate GeoJSON from recorded car positions.
        """
        if not self.location_points:
            return None

        output = MultiPoint(self.location_points)
        gdf = gpd.GeoSeries(output)
        gdf.crs = {"init": "epsg:4326"}
        return gdf
