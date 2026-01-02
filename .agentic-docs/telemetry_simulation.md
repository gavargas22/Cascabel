# Telemetry Simulation: Generating Realistic Sensor Data

## Overview
Generate synthetic telemetry data that matches the format and characteristics of real mobile device sensor data collected during car queue movement.

## Data Format Analysis

### Key Sensor Categories
Based on raw CSV data analysis:

1. **GPS/Location Data**
   - Latitude, Longitude, Altitude
   - Speed, Course (heading)
   - Horizontal/Vertical Accuracy
   - Timestamp

2. **Accelerometer Data**
   - X, Y, Z acceleration components
   - Timestamp

3. **Gyroscope Data**
   - X, Y, Z rotation rates
   - Timestamp

4. **Motion Data**
   - Yaw, Roll, Pitch
   - User acceleration (device-motion corrected)
   - Attitude quaternions
   - Gravity vector
   - Rotation rates

5. **Activity Recognition**
   - Activity type ("automotive")
   - Confidence level

6. **Device Metadata**
   - Orientation
   - Floor level
   - Network info

## Physics-Based Telemetry Generation

### Car Movement Physics
```python
class CarPhysics:
    def __init__(self, mass=1500, max_acceleration=3.0, max_velocity=25.0):
        self.mass = mass  # kg
        self.max_acceleration = max_acceleration  # m/s²
        self.max_velocity = max_velocity  # m/s
        self.current_velocity = 0.0
        self.current_acceleration = 0.0
        self.position = 0.0  # along waitline

    def update_physics(self, target_velocity, dt):
        """Update car physics based on target velocity"""
        # Calculate required acceleration
        velocity_diff = target_velocity - self.current_velocity
        required_acceleration = velocity_diff / dt

        # Limit acceleration
        self.current_acceleration = np.clip(
            required_acceleration,
            -self.max_acceleration,
            self.max_acceleration
        )

        # Update velocity
        self.current_velocity += self.current_acceleration * dt
        self.current_velocity = np.clip(
            self.current_velocity, 0, self.max_velocity
        )

        # Update position
        self.position += self.current_velocity * dt

        return self.current_acceleration, self.current_velocity, self.position
```

### GPS Position Generation
```python
class GPSGenerator:
    def __init__(self, waitline, horizontal_accuracy=5.0, vertical_accuracy=3.0):
        self.waitline = waitline
        self.h_accuracy = horizontal_accuracy
        self.v_accuracy = vertical_accuracy

    def generate_position(self, distance_along_path):
        """Generate GPS coordinates with noise"""
        # Get true position
        true_position = self.waitline.compute_position_at_distance_from_start(
            distance_along_path
        )

        # Add GPS noise
        lat_noise = np.random.normal(0, self.h_accuracy / 111320)  # degrees
        lon_noise = np.random.normal(0, self.h_accuracy / 111320)  # degrees
        alt_noise = np.random.normal(0, self.v_accuracy)

        noisy_lat = true_position.y + lat_noise
        noisy_lon = true_position.x + lon_noise
        noisy_alt = true_position.z + alt_noise if hasattr(true_position, 'z') else alt_noise

        return {
            'latitude': noisy_lat,
            'longitude': noisy_lon,
            'altitude': noisy_alt,
            'horizontal_accuracy': self.h_accuracy,
            'vertical_accuracy': self.v_accuracy
        }
```

### Accelerometer Simulation
```python
class AccelerometerGenerator:
    def __init__(self, noise_std=0.01):
        self.noise_std = noise_std  # m/s²
        self.gravity = np.array([0, 0, -9.81])  # gravity vector

    def generate_acceleration(self, car_acceleration, device_orientation):
        """Generate accelerometer readings"""
        # Device acceleration (car acceleration + gravity)
        device_accel = np.array([
            car_acceleration[0],  # forward/backward
            car_acceleration[1],  # left/right
            car_acceleration[2]   # up/down
        ])

        # Apply device orientation transformation
        device_accel = self.apply_device_orientation(device_accel, device_orientation)

        # Add gravity
        total_accel = device_accel + self.gravity

        # Add noise
        noise = np.random.normal(0, self.noise_std, 3)
        noisy_accel = total_accel + noise

        return {
            'accelerometerAccelerationX': noisy_accel[0],
            'accelerometerAccelerationY': noisy_accel[1],
            'accelerometerAccelerationZ': noisy_accel[2]
        }

    def apply_device_orientation(self, acceleration, orientation):
        """Transform acceleration based on device orientation"""
        if orientation == "portrait":
            # Phone upright, screen facing user
            return np.array([acceleration[1], acceleration[2], acceleration[0]])
        elif orientation == "landscape":
            # Phone sideways
            return np.array([acceleration[0], acceleration[2], -acceleration[1]])
        else:  # flat
            return acceleration
```

### Gyroscope and Motion Data
```python
class MotionGenerator:
    def __init__(self, gyro_noise_std=0.001):
        self.gyro_noise_std = gyro_noise_std

    def generate_motion_data(self, car_velocity, car_yaw_rate, device_orientation):
        """Generate comprehensive motion data"""
        # Gyroscope (rotation rates)
        true_rotation = np.array([
            0.0,  # roll rate
            0.0,  # pitch rate
            car_yaw_rate  # yaw rate from car turning
        ])

        # Add noise
        gyro_noise = np.random.normal(0, self.gyro_noise_std, 3)
        noisy_gyro = true_rotation + gyro_noise

        # Attitude (orientation in space)
        yaw = np.random.normal(0, 0.1)  # small random variations
        roll = np.random.normal(0, 0.05)
        pitch = np.random.normal(0, 0.05)

        # Convert to quaternions
        qw, qx, qy, qz = self.euler_to_quaternion(yaw, pitch, roll)

        # User acceleration (device motion corrected)
        user_accel = self.calculate_user_acceleration(car_velocity, device_orientation)

        return {
            'gyroRotationX': noisy_gyro[0],
            'gyroRotationY': noisy_gyro[1],
            'gyroRotationZ': noisy_gyro[2],
            'motionYaw': yaw,
            'motionRoll': roll,
            'motionPitch': pitch,
            'motionQuaternionW': qw,
            'motionQuaternionX': qx,
            'motionQuaternionY': qy,
            'motionQuaternionZ': qz,
            'motionUserAccelerationX': user_accel[0],
            'motionUserAccelerationY': user_accel[1],
            'motionUserAccelerationZ': user_accel[2]
        }

    def euler_to_quaternion(self, yaw, pitch, roll):
        """Convert Euler angles to quaternion"""
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)

        qw = cy * cp * cr + sy * sp * sr
        qx = cy * cp * sr - sy * sp * cr
        qy = sy * cp * sr + cy * sp * cr
        qz = sy * cp * cr - cy * sp * sr

        return qw, qx, qy, qz
```

## Telemetry Data Integration
```python
class TelemetryGenerator:
    def __init__(self, waitline, phone_config):
        self.waitline = waitline
        self.gps_gen = GPSGenerator(waitline,
                                   phone_config.get('gps_noise', {}).get('horizontal_accuracy', 5.0))
        self.accel_gen = AccelerometerGenerator(phone_config.get('accelerometer_noise', 0.01))
        self.motion_gen = MotionGenerator(phone_config.get('gyro_noise', 0.001))
        self.sampling_rate = phone_config.get('sampling_rate', 10)
        self.device_orientation = phone_config.get('device_orientation', 'portrait')

    def generate_telemetry_record(self, car, timestamp):
        """Generate complete telemetry record for a car at given time"""
        # Get car physics data
        acceleration = car.current_acceleration
        velocity = car.current_velocity
        position = car.current_position

        # Generate sensor data
        gps_data = self.gps_gen.generate_position(position)
        accel_data = self.accel_gen.generate_acceleration(
            acceleration, self.device_orientation
        )
        motion_data = self.motion_gen.generate_motion_data(
            velocity, 0.0, self.device_orientation  # assuming straight path
        )

        # Combine all data
        record = {
            'loggingTime': timestamp.strftime('%H:%M.%S.%f')[:-3],
            'loggingSample': int(timestamp.timestamp() * self.sampling_rate) % 1000000,
            'locationTimestamp_since1970': int(timestamp.timestamp()),
            'locationLatitude': gps_data['latitude'],
            'locationLongitude': gps_data['longitude'],
            'locationAltitude': gps_data['altitude'],
            'locationSpeed': velocity * 3.6,  # m/s to km/h
            'locationCourse': 0.0,  # heading (north = 0)
            'locationHorizontalAccuracy': gps_data['horizontal_accuracy'],
            'locationVerticalAccuracy': gps_data['vertical_accuracy'],
            **accel_data,
            **motion_data,
            'activity': 'automotive',
            'activityActivityConfidence': 2,
            'deviceOrientation': self.device_orientation
        }

        return record
```

## CSV Generation
```python
import csv
from io import StringIO

class CSVGenerator:
    def __init__(self):
        self.fieldnames = [
            'loggingTime', 'loggingSample', 'locationTimestamp_since1970',
            'locationLatitude', 'locationLongitude', 'locationAltitude',
            'locationSpeed', 'locationCourse', 'locationHorizontalAccuracy',
            'locationVerticalAccuracy', 'locationFloor', 'locationHeadingTimestamp_since1970',
            'locationHeadingX', 'locationHeadingY', 'locationHeadingZ',
            'locationTrueHeading', 'locationMagneticHeading', 'locationHeadingAccuracy',
            'accelerometerTimestamp_sinceReboot', 'accelerometerAccelerationX',
            'accelerometerAccelerationY', 'accelerometerAccelerationZ',
            'gyroTimestamp_sinceReboot', 'gyroRotationX', 'gyroRotationY', 'gyroRotationZ',
            'motionTimestamp_sinceReboot', 'motionYaw', 'motionRoll', 'motionPitch',
            'motionRotationRateX', 'motionRotationRateY', 'motionRotationRateZ',
            'motionUserAccelerationX', 'motionUserAccelerationY', 'motionUserAccelerationZ',
            'motionAttitudeReferenceFrame', 'motionQuaternionX', 'motionQuaternionY',
            'motionQuaternionZ', 'motionQuaternionW', 'motionGravityX', 'motionGravityY',
            'motionGravityZ', 'motionMagneticFieldX', 'motionMagneticFieldY',
            'motionMagneticFieldZ', 'motionMagneticFieldCalibrationAccuracy',
            'activityTimestamp_sinceReboot', 'activity', 'activityActivityConfidence',
            'activityActivityStartDate', 'pedometerStartDate', 'pedometerNumberofSteps',
            'pedometerDistance', 'pedometerFloorAscended', 'pedometerFloorDescended',
            'pedometerEndDate', 'altimeterTimestamp_sinceReboot', 'altimeterReset',
            'altimeterRelativeAltitude', 'altimeterPressure', 'IP_en0', 'IP_pdp_ip0',
            'deviceOrientation', 'state'
        ]

    def generate_csv(self, telemetry_records):
        """Generate CSV string from telemetry records"""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fieldnames)
        writer.writeheader()

        for record in telemetry_records:
            # Fill missing fields with defaults
            complete_record = {field: record.get(field, '') for field in self.fieldnames}
            # Set some defaults for missing data
            complete_record.update({
                'locationFloor': -9999,
                'motionAttitudeReferenceFrame': 'XArbitraryZVertical',
                'motionMagneticFieldCalibrationAccuracy': -1,
                'altimeterReset': 0,
                'altimeterRelativeAltitude': 0.00390625,
                'altimeterPressure': 88.53694,
                'IP_en0': '0.0.0.0',
                'IP_pdp_ip0': '33.234.95.54',
                'state': 0
            })
            writer.writerow(complete_record)

        return output.getvalue()
```

## Validation and Calibration

### Sensor Noise Models
- **GPS**: Gaussian noise with configurable standard deviation
- **Accelerometer**: White noise plus bias drift
- **Gyroscope**: Angle random walk noise

### Physics Validation
- Acceleration should integrate to velocity
- Velocity should integrate to position
- Accelerometer readings should match car acceleration + gravity

### Real Data Comparison
- Statistical comparison with raw CSV data
- Distribution analysis of sensor values
- Correlation analysis between sensors

## Future Enhancements

### Lane Switching Gyroscope Simulation
When cars switch lanes, the gyroscope will detect rotational motion:

```python
def simulate_lane_change_gyro(car, lane_change_angle, duration):
    """
    Generate gyroscope data for a lane change maneuver.

    Args:
        car: Car object
        lane_change_angle: Angle of lane change in degrees
        duration: Duration of the maneuver in seconds
    """
    # Convert angle to radians
    angle_rad = math.radians(lane_change_angle)

    # Calculate angular velocity (angle/time)
    angular_velocity = angle_rad / duration

    # Generate gyroscope readings during turn
    gyro_readings = []
    for t in np.linspace(0, duration, int(duration * sampling_rate)):
        # Smooth angular velocity profile (ease in/out)
        progress = t / duration
        velocity_factor = 4 * progress * (1 - progress)  # Bell curve
        current_angular_vel = angular_velocity * velocity_factor

        gyro_reading = {
            'gyroRotationX': 0.0,  # Roll
            'gyroRotationY': 0.0,  # Pitch
            'gyroRotationZ': current_angular_vel  # Yaw
        }
        gyro_readings.append(gyro_reading)

    return gyro_readings
```

### Multi-Lane Coordinate Systems
Future versions will support multiple lanes with independent coordinate systems:

```python
class MultiLanePath:
    def __init__(self, crossing_geojson):
        self.lanes = self.parse_lanes_from_geojson(crossing_geojson)
        self.lane_coordinates = {}

        for lane_id, lane_geometry in self.lanes.items():
            self.lane_coordinates[lane_id] = self.convert_to_utm(lane_geometry)

    def get_lane_position(self, lane_id, distance_along_lane):
        """Get GPS coordinates for a position in a specific lane"""
        return self.lane_coordinates[lane_id].interpolate(distance_along_lane)
```

### Sensor Fusion Validation
Future validation will ensure all sensors are properly correlated during lane changes:
- GPS position changes match the lane switch geometry
- Accelerometer shows lateral acceleration during turns
- Gyroscope angular velocity integrates to the correct heading change
- All sensors timestamp-aligned for realistic data streams