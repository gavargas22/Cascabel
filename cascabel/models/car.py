from shapely.geometry import Point
import numpy as np
from datetime import datetime
from .models import PhoneConfig, CarState


class Car:
    """
    Car Model with Physics Simulation
    =================================

    Enhanced car model that simulates realistic vehicle physics for queue movement.
    Generates telemetry data matching mobile device sensor formats.
    Each car has its own dynamic path from a random starting point to the border crossing.
    """

    def __init__(
        self, car_id, sampling_rate=10, phone_config=None, initial_position=0.0, waitline=None
    ):
        self.car_id = car_id
        self.sampling_rate = sampling_rate

        # Use Pydantic model for phone configuration
        if phone_config:
            if isinstance(phone_config, dict):
                self.phone_config = PhoneConfig(**phone_config)
            else:
                # Assume it's already a PhoneConfig object
                self.phone_config = phone_config
        else:
            self.phone_config = PhoneConfig()

        # Dynamic path for this car (can be unique per car)
        self.waitline = waitline  # DynamicWaitLine or regular WaitLine

        # Physics properties (typical passenger car in border crossing scenario)
        self.mass = 1500  # kg
        self.max_acceleration = 0.75  # m/s² (gentle acceleration - realistic for queue)
        self.max_deceleration = -1.25  # m/s² (gentle braking - realistic for queue)
        self.max_velocity = 13.4112  # m/s (30 mph exact = 48 km/h for approach)
        self.queue_velocity = 1.34112  # m/s (3 mph exact = 4.8 km/h for queue movement)
        self.length = 4.5  # meters

        # State tracking
        self.position = initial_position  # meters along waitline
        self.velocity = 0.0  # m/s
        self.acceleration = 0.0  # m/s²

        # Queue status
        self.status = "arriving"  # arriving, queued, serving, completed
        self.queue_id = None
        self.arrival_time = None
        self.queue_start_time = None  # When car first entered queued state (blocked by traffic)
        self.service_start_time = None
        self.completion_time = None
        self.exit_time = None  # When car exits the system (removed from simulation)
        self.wait_time = None  # Calculated: service_start_time - queue_start_time

        # Journey statistics
        self.total_distance = 0.0  # Total distance traveled (meters)
        self.max_speed_reached = 0.0  # Maximum speed during journey (m/s)
        self.avg_speed = 0.0  # Average speed during journey (m/s)
        self.time_in_queue = 0.0  # Time spent in queued status (seconds)
        self.time_being_served = 0.0  # Time spent in serving status (seconds)
        self.time_approaching = 0.0  # Time spent in approaching status (seconds)

        # Speed samples for calculating average
        self._speed_samples = []
        self._last_position = initial_position
        self._last_update_time = None

        # Telemetry data storage
        self.telemetry_records = []

        # Telemetry generator will be initialized later with waitline
        self.telemetry_gen = None

    def set_telemetry_generator(self, waitline=None):
        """
        Initialize telemetry generator with waitline.

        Args:
            waitline: WaitLine object for path geometry (optional, uses car's own waitline if not provided)
        """
        if self.phone_config:
            from ..simulation.telemetry.telemetry_generator import TelemetryGenerator

            # Use provided waitline or car's own waitline
            path = waitline if waitline is not None else self.waitline
            if path:
                self.telemetry_gen = TelemetryGenerator(path, self.phone_config.dict())

    def generate_telemetry(self, timestamp):
        """
        Generate telemetry record for current car state.

        Args:
            timestamp: Current simulation timestamp

        Returns:
            dict: Telemetry record or None if generator not available
        """
        if not self.telemetry_gen:
            return None

        record = self.telemetry_gen.generate_telemetry_record(self, timestamp)
        self.telemetry_records.append(record)
        return record

    def get_state(self) -> CarState:
        """
        Get current car state as Pydantic model.

        Returns:
            CarState: Current car state
        """
        return CarState(
            car_id=self.car_id,
            position=self.position,
            velocity=self.velocity,
            acceleration=self.acceleration,
            status=self.status,  # type: ignore
            queue_id=self.queue_id,
            arrival_time=self.arrival_time,
            service_start_time=self.service_start_time,
            completion_time=self.completion_time,
        )

    def update_statistics(self, current_time, dt):
        """
        Update journey statistics.

        Args:
            current_time: Current simulation time (seconds)
            dt: Time delta (seconds)
        """
        # Track time in each status
        if self.status == "approaching":
            self.time_approaching += dt
        elif self.status == "queued":
            self.time_in_queue += dt
        elif self.status == "serving":
            self.time_being_served += dt

        # Track distance
        if self._last_position is not None:
            distance_delta = abs(self.position - self._last_position)
            self.total_distance += distance_delta
        self._last_position = self.position

        # Track speed
        self.max_speed_reached = max(self.max_speed_reached, abs(self.velocity))
        self._speed_samples.append(abs(self.velocity))

        # Calculate average speed
        if self._speed_samples:
            self.avg_speed = sum(self._speed_samples) / len(self._speed_samples)

        self._last_update_time = current_time

    def update_physics(self, target_velocity, dt):
        """
        Update car physics based on target velocity and time step.

        Args:
            target_velocity: Desired velocity (m/s)
            dt: Time step (seconds)
        """
        # Calculate required acceleration
        velocity_diff = target_velocity - self.velocity
        required_acceleration = velocity_diff / dt if dt > 0 else 0

        # Limit acceleration/deceleration
        max_accel = (
            self.max_acceleration
            if required_acceleration >= 0
            else self.max_deceleration
        )
        self.acceleration = np.clip(
            required_acceleration, self.max_deceleration, max_accel
        )

        # Update velocity
        self.velocity += self.acceleration * dt
        self.velocity = np.clip(self.velocity, 0, self.max_velocity)

        # Update position
        self.position += self.velocity * dt

    def get_varianced_value(self, value):
        """Add random variance to a value (legacy method)"""
        variance = np.random.uniform(-0.1, 0.1)
        result = value + (value * variance)
        return result

    def report_gps_position(self, parameter_list):
        """Legacy GPS reporting method"""
        return {"latitude": 0.0, "longitude": 0.0}

    def move(self, velocity, acceleration, time_interval):
        """Legacy move method - updated to use physics"""
        self.update_physics(velocity, time_interval)
        print(
            f"Car {self.car_id}: position={self.position:.2f}m, "
            f"velocity={self.velocity:.2f}m/s"
        )

    def set_status(self, status, timestamp=None):
        """Update car status with timestamp"""
        self.status = status
        # Set arrival_time when car first enters the system (approaching or queued)
        if status in ["approaching", "queued"] and not self.arrival_time:
            self.arrival_time = timestamp or datetime.now().timestamp()

        # Set queue_start_time when first entering queued state (blocked by traffic)
        if status == "queued" and not self.queue_start_time:
            self.queue_start_time = timestamp or datetime.now().timestamp()

        # Set service_start_time when service begins and calculate wait time
        if status == "serving" and not self.service_start_time:
            self.service_start_time = timestamp or datetime.now().timestamp()
            # Calculate wait time if we have queue_start_time
            if self.queue_start_time:
                self.wait_time = self.service_start_time - self.queue_start_time

        # Set completion_time when service completes
        if status == "completed" and not self.completion_time:
            self.completion_time = timestamp or datetime.now().timestamp()

    def get_waiting_time(self):
        """Calculate total waiting time in queue"""
        if self.service_start_time and self.arrival_time:
            return self.service_start_time - self.arrival_time
        return 0.0

    def get_service_time(self):
        """Calculate service time (crossing time)"""
        if self.completion_time and self.service_start_time:
            return self.completion_time - self.service_start_time
        return 0.0

    def get_total_journey_time(self):
        """Calculate total journey time from arrival to exit"""
        if self.exit_time and self.arrival_time:
            return self.exit_time - self.arrival_time
        elif self.completion_time and self.arrival_time:
            return self.completion_time - self.arrival_time
        return 0.0

    def get_comprehensive_stats(self):
        """Get comprehensive statistics for this car's journey"""
        return {
            "car_id": self.car_id,
            "status": self.status,
            "queue_id": self.queue_id,

            # Timing
            "arrival_time": self.arrival_time,
            "service_start_time": self.service_start_time,
            "completion_time": self.completion_time,
            "exit_time": self.exit_time,
            "wait_time": self.get_waiting_time(),
            "service_time": self.get_service_time(),
            "total_journey_time": self.get_total_journey_time(),

            # Time in each status
            "time_approaching": self.time_approaching,
            "time_in_queue": self.time_in_queue,
            "time_being_served": self.time_being_served,

            # Distance and speed
            "total_distance": self.total_distance,
            "max_speed": self.max_speed_reached,
            "avg_speed": self.avg_speed,
            "final_position": self.position,

            # Telemetry
            "telemetry_records_count": len(self.telemetry_records) if self.telemetry_records else 0,
        }

    def __repr__(self):
        return (
            f"Car(id={self.car_id}, status={self.status}, "
            f"pos={self.position:.1f}m, vel={self.velocity:.1f}m/s)"
        )
