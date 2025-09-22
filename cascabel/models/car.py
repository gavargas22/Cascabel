from shapely.geometry import Point
import numpy as np
from datetime import datetime


class Car():
    '''
    Car Model with Physics Simulation
    =================================

    Enhanced car model that simulates realistic vehicle physics for queue movement.
    Generates telemetry data matching mobile device sensor formats.
    '''
    def __init__(self, car_id, sampling_rate=10, phone_config=None, initial_position=0.0):
        self.car_id = car_id
        self.sampling_rate = sampling_rate
        self.phone_config = phone_config or {}

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
        self.arrival_time = None
        self.service_start_time = None
        self.completion_time = None

        # Telemetry data storage
        self.telemetry_records = []

        # Legacy compatibility
        self.current_state = {
            "time": 0,
            "position": initial_position,
            "speed": 0.0,
            "odometer": 0.0
        }
        self.initial_state = self.current_state.copy()

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
        max_accel = self.max_acceleration if required_acceleration >= 0 else self.max_deceleration
        self.acceleration = np.clip(required_acceleration, self.max_deceleration, max_accel)

        # Update velocity
        self.velocity += self.acceleration * dt
        self.velocity = np.clip(self.velocity, 0, self.max_velocity)

        # Update position
        self.position += self.velocity * dt

        # Update legacy state
        self.current_state["position"] = self.position
        self.current_state["speed"] = self.velocity
        self.current_state["odometer"] = self.position

    def get_varianced_value(self, value):
        """Add random variance to a value (legacy method)"""
        variance = np.random.uniform(-0.1, 0.1)
        result = value + (value * variance)
        return result

    def report_gps_position(self, parameter_list):
        """Legacy GPS reporting method"""
        return (
            {
                "latitude": 0.0,
                "longitude": 0.0
            }
        )

    def move(self, velocity, acceleration, time_interval):
        """Legacy move method - updated to use physics"""
        self.update_physics(velocity, time_interval)
        print(f"Car {self.car_id}: position={self.position:.2f}m, velocity={self.velocity:.2f}m/s")

    def set_status(self, status, timestamp=None):
        """Update car status with timestamp"""
        self.status = status
        if status == "queued" and not self.arrival_time:
            self.arrival_time = timestamp or datetime.now()
        elif status == "serving" and not self.service_start_time:
            self.service_start_time = timestamp or datetime.now()
        elif status == "completed" and not self.completion_time:
            self.completion_time = timestamp or datetime.now()

    def get_waiting_time(self):
        """Calculate total waiting time in queue"""
        if self.service_start_time and self.arrival_time:
            return (self.service_start_time - self.arrival_time).total_seconds()
        return 0.0

    def get_service_time(self):
        """Calculate service time (crossing time)"""
        if self.completion_time and self.service_start_time:
            return (self.completion_time - self.service_start_time).total_seconds()
        return 0.0

    def __repr__(self):
        return f"Car(id={self.car_id}, status={self.status}, pos={self.position:.1f}m, vel={self.velocity:.1f}m/s)"
