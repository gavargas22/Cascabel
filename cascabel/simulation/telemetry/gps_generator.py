import numpy as np


class GPSGenerator:
    """
    GPS Position Generator with Realistic Noise
    ==========================================

    Generates GPS coordinates along a path with configurable accuracy noise.
    """

    def __init__(self, waitline, horizontal_accuracy=5.0, vertical_accuracy=3.0):
        """
        Initialize GPS generator.

        Args:
            waitline: WaitLine object with path geometry
            horizontal_accuracy: GPS horizontal accuracy in meters
            vertical_accuracy: GPS vertical accuracy in meters
        """
        self.waitline = waitline
        self.h_accuracy = horizontal_accuracy
        self.v_accuracy = vertical_accuracy

    def generate_position(self, distance_along_path):
        """
        Generate GPS coordinates with noise at given distance along path.

        Args:
            distance_along_path: Distance in meters from path start

        Returns:
            Dict with lat, lon, alt, and accuracy values
        """
        # Get true position from waitline
        try:
            true_position = self.waitline.compute_position_at_distance_from_start(distance_along_path)
            true_lat = true_position.y
            true_lon = true_position.x
            true_alt = getattr(true_position, 'z', 0.0)  # Default altitude if not available
        except Exception:
            # Fallback if position calculation fails
            true_lat = 31.7660026
            true_lon = -106.4510884
            true_alt = 1133.354

        # Add GPS noise (Gaussian distribution)
        # Convert accuracy from meters to degrees (approximate)
        lat_noise_deg = np.random.normal(0, self.h_accuracy / 111320)  # 1 degree lat ≈ 111.32 km
        lon_noise_deg = np.random.normal(0, self.h_accuracy / 111320)  # 1 degree lon ≈ 111.32 km at equator
        alt_noise = np.random.normal(0, self.v_accuracy)

        noisy_lat = true_lat + lat_noise_deg
        noisy_lon = true_lon + lon_noise_deg
        noisy_alt = true_alt + alt_noise

        return {
            'latitude': noisy_lat,
            'longitude': noisy_lon,
            'altitude': noisy_alt,
            'horizontal_accuracy': self.h_accuracy + np.random.normal(0, 1),
            'vertical_accuracy': self.v_accuracy + np.random.normal(0, 0.5)
        }

    def generate_position_at_time(self, car, timestamp):
        """
        Generate GPS position for a car at specific time.

        Args:
            car: Car object with current position
            timestamp: Timestamp for the reading

        Returns:
            GPS data dict
        """
        return self.generate_position(car.position)