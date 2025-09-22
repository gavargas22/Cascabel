import numpy as np
import math


class MotionGenerator:
    """
    Motion Data Generator
    ====================

    Generates gyroscope, attitude, and motion data for realistic device simulation.
    """

    def __init__(self, gyro_noise_std=0.001, accel_noise_std=0.01):
        """
        Initialize motion generator.

        Args:
            gyro_noise_std: Gyroscope noise standard deviation (rad/s)
            accel_noise_std: Accelerometer noise for user acceleration
        """
        self.gyro_noise_std = gyro_noise_std
        self.accel_noise_std = accel_noise_std

    def generate_motion_data(self, car_velocity, car_yaw_rate=0.0, device_orientation="portrait"):
        """
        Generate comprehensive motion data.

        Args:
            car_velocity: Car velocity (m/s)
            car_yaw_rate: Car turning rate (rad/s)
            device_orientation: Device orientation

        Returns:
            Dict with motion sensor data
        """
        # Gyroscope (rotation rates in device coordinates)
        gyro_data = self._generate_gyroscope_data(car_yaw_rate, device_orientation)

        # Attitude (device orientation in space)
        attitude_data = self._generate_attitude_data(device_orientation)

        # User acceleration (device motion minus gravity)
        user_accel_data = self._generate_user_acceleration(car_velocity, device_orientation)

        # Magnetic field (simulated)
        magnetic_data = self._generate_magnetic_field()

        return {
            **gyro_data,
            **attitude_data,
            **user_accel_data,
            **magnetic_data,
            'motionAttitudeReferenceFrame': 'XArbitraryZVertical'
        }

    def _generate_gyroscope_data(self, car_yaw_rate, device_orientation):
        """
        Generate gyroscope readings.

        Args:
            car_yaw_rate: Car's turning rate
            device_orientation: Device orientation

        Returns:
            Gyroscope data dict
        """
        # Base rotation rates (small random variations)
        roll_rate = np.random.normal(0, 0.01)  # rad/s
        pitch_rate = np.random.normal(0, 0.01)  # rad/s
        yaw_rate = car_yaw_rate + np.random.normal(0, 0.005)  # rad/s

        # Transform to device coordinates
        if device_orientation == "portrait":
            # Device Y axis aligns with car forward direction
            gyro_x = roll_rate   # Roll around device X
            gyro_y = pitch_rate  # Pitch around device Y
            gyro_z = yaw_rate    # Yaw around device Z
        elif device_orientation == "landscape":
            gyro_x = pitch_rate
            gyro_y = roll_rate
            gyro_z = yaw_rate
        else:  # flat
            gyro_x = roll_rate
            gyro_y = yaw_rate
            gyro_z = pitch_rate

        # Add noise
        noise = np.random.normal(0, self.gyro_noise_std, 3)
        noisy_gyro = np.array([gyro_x, gyro_y, gyro_z]) + noise

        return {
            'gyroRotationX': noisy_gyro[0],
            'gyroRotationY': noisy_gyro[1],
            'gyroRotationZ': noisy_gyro[2]
        }

    def _generate_attitude_data(self, device_orientation):
        """
        Generate device attitude (orientation) data.

        Args:
            device_orientation: Device orientation

        Returns:
            Attitude data dict
        """
        # Generate small random variations in orientation
        yaw = np.random.normal(0, np.radians(2))    # ±2 degrees
        roll = np.random.normal(0, np.radians(1))   # ±1 degree
        pitch = np.random.normal(0, np.radians(1))  # ±1 degree

        # Adjust based on device orientation
        if device_orientation == "portrait":
            # Phone upright
            roll += np.radians(0)  # No adjustment
            pitch += np.radians(0)
        elif device_orientation == "landscape":
            # Phone sideways
            roll += np.radians(90)
        # Flat orientation has default values

        # Convert to quaternion
        qw, qx, qy, qz = self._euler_to_quaternion(yaw, pitch, roll)

        return {
            'motionYaw': yaw,
            'motionRoll': roll,
            'motionPitch': pitch,
            'motionQuaternionW': qw,
            'motionQuaternionX': qx,
            'motionQuaternionY': qy,
            'motionQuaternionZ': qz
        }

    def _generate_user_acceleration(self, car_velocity, device_orientation):
        """
        Generate user acceleration (device acceleration minus gravity).

        Args:
            car_velocity: Car velocity
            device_orientation: Device orientation

        Returns:
            User acceleration data dict
        """
        # User acceleration is device acceleration with gravity removed
        # For simplicity, add small random accelerations
        user_accel_x = np.random.normal(0, self.accel_noise_std)
        user_accel_y = np.random.normal(0, self.accel_noise_std)
        user_accel_z = np.random.normal(0, self.accel_noise_std)

        # Scale based on car movement
        speed_factor = min(car_velocity / 10.0, 1.0)  # Scale with speed
        user_accel_x *= (1 + speed_factor * 0.5)
        user_accel_y *= (1 + speed_factor * 0.5)

        return {
            'motionUserAccelerationX': user_accel_x,
            'motionUserAccelerationY': user_accel_y,
            'motionUserAccelerationZ': user_accel_z
        }

    def _generate_magnetic_field(self):
        """
        Generate simulated magnetic field readings.

        Returns:
            Magnetic field data dict
        """
        # Typical Earth's magnetic field components (microtesla)
        # These would vary by location, but we'll use constants
        mag_x = np.random.normal(20.0, 2.0)   # East component
        mag_y = np.random.normal(0.0, 2.0)    # North component
        mag_z = np.random.normal(40.0, 2.0)   # Down component

        return {
            'motionMagneticFieldX': mag_x,
            'motionMagneticFieldY': mag_y,
            'motionMagneticFieldZ': mag_z,
            'motionMagneticFieldCalibrationAccuracy': -1  # Uncalibrated
        }

    def _euler_to_quaternion(self, yaw, pitch, roll):
        """
        Convert Euler angles to quaternion.

        Args:
            yaw: Yaw angle (radians)
            pitch: Pitch angle (radians)
            roll: Roll angle (radians)

        Returns:
            Quaternion components (w, x, y, z)
        """
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        qw = cy * cp * cr + sy * sp * sr
        qx = cy * cp * sr - sy * sp * cr
        qy = sy * cp * sr + cy * sp * cr
        qz = sy * cp * cr - cy * sp * sr

        return qw, qx, qy, qz