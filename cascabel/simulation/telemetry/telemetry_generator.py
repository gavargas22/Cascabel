from datetime import datetime, timedelta
from .gps_generator import GPSGenerator
from .accelerometer_generator import AccelerometerGenerator
from .motion_generator import MotionGenerator


class TelemetryGenerator:
    """
    Main Telemetry Generator
    ========================

    Coordinates all sensor generators to create complete telemetry records
    matching the format of real mobile device data.
    """

    def __init__(self, waitline, phone_config):
        """
        Initialize telemetry generator.

        Args:
            waitline: WaitLine object for path geometry
            phone_config: Phone/device configuration parameters
        """
        self.waitline = waitline
        self.phone_config = phone_config

        # Initialize sensor generators
        self.gps_gen = GPSGenerator(
            waitline,
            horizontal_accuracy=phone_config.get('gps_noise', {}).get('horizontal_accuracy', 5.0),
            vertical_accuracy=phone_config.get('gps_noise', {}).get('vertical_accuracy', 3.0)
        )

        self.accel_gen = AccelerometerGenerator(
            noise_std=phone_config.get('accelerometer_noise', 0.01)
        )

        self.motion_gen = MotionGenerator(
            gyro_noise_std=phone_config.get('gyro_noise', 0.001),
            accel_noise_std=phone_config.get('accelerometer_noise', 0.01)
        )

        # Phone parameters
        self.sampling_rate = phone_config.get('sampling_rate', 10)
        self.device_orientation = phone_config.get('device_orientation', 'portrait')

    def generate_telemetry_record(self, car, timestamp):
        """
        Generate complete telemetry record for a car at given time.

        Args:
            car: Car object with current physics state
            timestamp: Timestamp for the reading

        Returns:
            Complete telemetry record dict
        """
        # Generate GPS data
        gps_data = self.gps_gen.generate_position_at_time(car, timestamp)

        # Generate accelerometer data
        car_acceleration = [car.acceleration, 0.0, 0.0]  # [forward, lateral, vertical]
        accel_data = self.accel_gen.generate_acceleration(
            car_acceleration, self.device_orientation
        )

        # Generate motion data
        motion_data = self.motion_gen.generate_motion_data(
            car.velocity, car_yaw_rate=0.0, device_orientation=self.device_orientation
        )

        # Combine all data into complete record
        record = {
            # Timing
            'loggingTime': timestamp.strftime('%H:%M.%S.%f')[:-3],
            'loggingSample': int(timestamp.timestamp() * self.sampling_rate) % 1000000,
            'locationTimestamp_since1970': int(timestamp.timestamp()),

            # GPS/Location
            'locationLatitude': gps_data['latitude'],
            'locationLongitude': gps_data['longitude'],
            'locationAltitude': gps_data['altitude'],
            'locationSpeed': car.velocity * 3.6,  # m/s to km/h
            'locationCourse': 0.0,  # heading (0 = north)
            'locationHorizontalAccuracy': gps_data['horizontal_accuracy'],
            'locationVerticalAccuracy': gps_data['vertical_accuracy'],
            'locationFloor': -9999,  # Not applicable
            'locationHeadingTimestamp_since1970': int(timestamp.timestamp()),
            'locationHeadingX': 0.0,  # Magnetometer data (simplified)
            'locationHeadingY': 0.0,
            'locationHeadingZ': 0.0,
            'locationTrueHeading': 0.0,
            'locationMagneticHeading': 0.0,
            'locationHeadingAccuracy': -1,

            # Accelerometer
            'accelerometerTimestamp_sinceReboot': int((timestamp - datetime(1970, 1, 1)).total_seconds() * 1000) % 100000,
            **accel_data,

            # Gyroscope
            'gyroTimestamp_sinceReboot': int((timestamp - datetime(1970, 1, 1)).total_seconds() * 1000) % 100000,

            # Motion data
            'motionTimestamp_sinceReboot': int((timestamp - datetime(1970, 1, 1)).total_seconds() * 1000) % 100000,

            # Activity recognition
            'activity': 'automotive',
            'activityActivityConfidence': 2,  # High confidence
            'activityActivityStartDate': timestamp.strftime('%H:%M.%S'),

            # Pedometer (not applicable for cars)
            'pedometerStartDate': '',
            'pedometerNumberofSteps': 0,
            'pedometerDistance': 0.0,
            'pedometerFloorAscended': 0,
            'pedometerFloorDescended': 0,
            'pedometerEndDate': '',

            # Altimeter
            'altimeterTimestamp_sinceReboot': int((timestamp - datetime(1970, 1, 1)).total_seconds() * 1000) % 100000,
            'altimeterReset': 0,
            'altimeterRelativeAltitude': 0.00390625,
            'altimeterPressure': 88.53694,

            # Network info
            'IP_en0': '0.0.0.0',
            'IP_pdp_ip0': '33.234.95.54',

            # Device info
            'deviceOrientation': self.device_orientation,
            'state': 0
        }

        # Add motion data
        record.update(motion_data)

        return record

    def generate_telemetry_for_car(self, car, start_time, duration_seconds):
        """
        Generate telemetry records for a car over a time period.

        Args:
            car: Car object
            start_time: Start timestamp
            duration_seconds: Duration to generate data for

        Returns:
            List of telemetry records
        """
        records = []
        current_time = start_time

        end_time = start_time + timedelta(seconds=duration_seconds)
        sample_interval = 1.0 / self.sampling_rate

        while current_time < end_time:
            record = self.generate_telemetry_record(car, current_time)
            records.append(record)
            current_time += timedelta(seconds=sample_interval)

        return records