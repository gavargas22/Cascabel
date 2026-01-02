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
    """

    def __init__(
        self, car_id, sampling_rate=10, phone_config=None, initial_position=0.0
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

        # Physics properties (typical passenger car)
        self.mass = 1500  # kg
        self.max_acceleration = 3.0  # m/s²
        self.max_deceleration = -5.0  # m/s² (braking)
        self.max_velocity = 25.0  # m/s (90 km/h)
        self.length = 4.5  # meters

        # State tracking
        self.position = initial_position  # meters along waitline
        self.velocity = 0.0  # m/s
        self.acceleration = 0.0  # m/s²

        # Queue status
        self.status = "arriving"  # arriving, queued, serving, completed
        self.queue_id = None
        self.arrival_time = None
        self.service_start_time = None
        self.completion_time = None

        # Telemetry data storage
        self.telemetry_records = []

        # Telemetry generator will be initialized later with waitline
        self.telemetry_gen = None

    def set_telemetry_generator(self, waitline):
        """
        Initialize telemetry generator with waitline.

        Args:
            waitline: WaitLine object for path geometry
        """
        if self.phone_config:
            from ..simulation.telemetry.telemetry_generator import TelemetryGenerator

            self.telemetry_gen = TelemetryGenerator(waitline, self.phone_config.dict())

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
        if status == "queued" and not self.arrival_time:
            self.arrival_time = timestamp or datetime.now().timestamp()
        elif status == "serving" and not self.service_start_time:
            self.service_start_time = timestamp or datetime.now().timestamp()
        elif status == "completed" and not self.completion_time:
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

    def __repr__(self):
        return (
            f"Car(id={self.car_id}, status={self.status}, "
            f"pos={self.position:.1f}m, vel={self.velocity:.1f}m/s)"
        )
