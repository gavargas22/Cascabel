import csv
from io import StringIO


class CSVGenerator:
    """
    CSV Data Generator
    =================

    Generates CSV files matching the format of real telemetry data.
    """

    def __init__(self):
        # Field names matching the raw CSV data format
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
        """
        Generate CSV string from telemetry records.

        Args:
            telemetry_records: List of telemetry record dictionaries

        Returns:
            CSV data as string
        """
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fieldnames)
        writer.writeheader()

        for record in telemetry_records:
            # Ensure all fields are present with defaults for missing data
            complete_record = {}
            for field in self.fieldnames:
                value = record.get(field, '')
                # Convert numeric types to strings, handle special cases
                if isinstance(value, float):
                    complete_record[field] = f"{value:.6f}" if abs(value) < 1000 else str(value)
                elif isinstance(value, int):
                    complete_record[field] = str(value)
                else:
                    complete_record[field] = str(value)

            writer.writerow(complete_record)

        return output.getvalue()

    def generate_csv_file(self, telemetry_records, filename):
        """
        Generate and save CSV file.

        Args:
            telemetry_records: List of telemetry record dictionaries
            filename: Output filename

        Returns:
            Number of records written
        """
        csv_content = self.generate_csv(telemetry_records)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)

        return len(telemetry_records)

    def validate_record(self, record):
        """
        Validate that a telemetry record has required fields.

        Args:
            record: Telemetry record dict

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'loggingTime', 'loggingSample', 'locationTimestamp_since1970',
            'locationLatitude', 'locationLongitude', 'accelerometerAccelerationX',
            'accelerometerAccelerationY', 'accelerometerAccelerationZ',
            'activity', 'activityActivityConfidence'
        ]

        for field in required_fields:
            if field not in record:
                return False

        return True

    def get_csv_stats(self, csv_content):
        """
        Get statistics about generated CSV content.

        Args:
            csv_content: CSV string

        Returns:
            Dict with statistics
        """
        lines = csv_content.strip().split('\n')
        num_records = len(lines) - 1  # Subtract header

        if num_records > 0:
            # Parse first data row to get sample values
            reader = csv.DictReader(StringIO(csv_content))
            first_row = next(reader)

            stats = {
                'total_records': num_records,
                'sample_latitude': float(first_row.get('locationLatitude', 0)),
                'sample_longitude': float(first_row.get('locationLongitude', 0)),
                'sample_speed': float(first_row.get('locationSpeed', 0)),
                'sample_activity': first_row.get('activity', ''),
                'csv_size_bytes': len(csv_content.encode('utf-8'))
            }
        else:
            stats = {
                'total_records': 0,
                'csv_size_bytes': len(csv_content.encode('utf-8'))
            }

        return stats