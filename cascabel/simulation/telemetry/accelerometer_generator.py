import numpy as np


class AccelerometerGenerator:
    """
    Accelerometer Data Generator
    ===========================

    Generates realistic accelerometer readings based on car physics
    and device orientation.
    """

    def __init__(self, noise_std=0.01):
        """
        Initialize accelerometer generator.

        Args:
            noise_std: Standard deviation of accelerometer noise (m/s²)
        """
        self.noise_std = noise_std
        self.gravity = np.array([0, 0, -9.81])  # Gravity vector in device coordinates

    def generate_acceleration(self, car_acceleration, device_orientation="portrait"):
        """
        Generate accelerometer readings for given car acceleration and device orientation.

        Args:
            car_acceleration: Car's acceleration vector [x, y, z] in m/s² (forward, lateral, vertical)
            device_orientation: Device orientation ("portrait", "landscape", "flat")

        Returns:
            Dict with accelerometer readings
        """
        # Convert car acceleration to device coordinates
        device_accel = self._car_to_device_acceleration(car_acceleration, device_orientation)

        # Add gravity (accelerometer measures specific force)
        total_accel = device_accel + self.gravity

        # Add noise
        noise = np.random.normal(0, self.noise_std, 3)
        noisy_accel = total_accel + noise

        return {
            'accelerometerAccelerationX': noisy_accel[0],
            'accelerometerAccelerationY': noisy_accel[1],
            'accelerometerAccelerationZ': noisy_accel[2]
        }

    def _car_to_device_acceleration(self, car_accel, orientation):
        """
        Transform car acceleration to device coordinate system.

        Args:
            car_accel: [forward, lateral, vertical] acceleration in car coordinates
            orientation: Device orientation

        Returns:
            Acceleration in device coordinates [x, y, z]
        """
        forward, lateral, vertical = car_accel

        if orientation == "portrait":
            # Phone upright, screen facing user
            # Car forward -> device -Y, car lateral -> device X
            return np.array([lateral, -forward, vertical])
        elif orientation == "landscape":
            # Phone sideways, screen facing user
            # Car forward -> device X, car lateral -> device Y
            return np.array([forward, lateral, vertical])
        elif orientation == "flat":
            # Phone flat on dashboard
            # Car forward -> device Y, car lateral -> device X
            return np.array([lateral, forward, vertical])
        else:
            # Default to portrait
            return np.array([lateral, -forward, vertical])

    def generate_acceleration_from_physics(self, car_velocity, car_acceleration, dt, device_orientation="portrait"):
        """
        Generate accelerometer data considering car physics and device motion.

        Args:
            car_velocity: Current car velocity vector
            car_acceleration: Current car acceleration vector
            dt: Time step
            device_orientation: Device orientation

        Returns:
            Accelerometer readings dict
        """
        # For more realistic simulation, consider centrifugal forces, etc.
        # For now, use basic transformation
        return self.generate_acceleration(car_acceleration, device_orientation)