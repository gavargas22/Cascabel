"""
Historical Data Ingestion Module
=================================

Processes raw telemetry CSV files to extract historical simulation data.
"""

import pandas as pd
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HistoricalDataIngestion:
    """
    Ingests historical telemetry data from CSV files.
    """

    def __init__(self, raw_data_dir: str = "raw_data"):
        """
        Initialize data ingestion.

        Args:
            raw_data_dir: Directory containing raw CSV files
        """
        self.raw_data_dir = raw_data_dir
        self.processed_data = []

    def load_all_csv_files(self) -> List[Dict[str, Any]]:
        """
        Load and process all CSV files in the raw data directory.

        Returns:
            List of processed trajectory data
        """
        trajectories = []

        if not os.path.exists(self.raw_data_dir):
            logger.warning(f"Raw data directory {self.raw_data_dir} not found")
            return trajectories

        csv_files = [f for f in os.listdir(self.raw_data_dir) if f.endswith(".csv")]

        for csv_file in csv_files:
            file_path = os.path.join(self.raw_data_dir, csv_file)
            try:
                trajectory = self.process_csv_file(file_path)
                if trajectory:
                    trajectories.append(trajectory)
            except Exception as e:
                logger.error(f"Failed to process {csv_file}: {e}")

        self.processed_data = trajectories
        return trajectories

    def process_csv_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a single CSV file to extract trajectory data.

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary with trajectory data or None if invalid
        """
        try:
            df = pd.read_csv(file_path)

            # Check if required columns exist
            required_cols = [
                "locationLatitude",
                "locationLongitude",
                "locationSpeed",
                "loggingTime",
            ]
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"Missing required columns in {file_path}")
                return None

            # Extract basic trajectory info
            trajectory = {
                "file_name": os.path.basename(file_path),
                "start_time": None,
                "end_time": None,
                "duration_seconds": None,
                "total_distance_km": 0.0,
                "average_speed_kmh": 0.0,
                "max_speed_kmh": 0.0,
                "points": [],
            }

            # Process GPS points
            latitudes = df["locationLatitude"].dropna()
            longitudes = df["locationLongitude"].dropna()
            speeds = df["locationSpeed"].dropna() * 3.6  # m/s to km/h
            times = df["loggingTime"].dropna()

            if len(latitudes) == 0:
                return None

            # Calculate trajectory metrics
            trajectory["max_speed_kmh"] = speeds.max() if len(speeds) > 0 else 0.0
            trajectory["average_speed_kmh"] = speeds.mean() if len(speeds) > 0 else 0.0

            # Extract time range
            if len(times) > 0:
                trajectory["start_time"] = str(times.iloc[0])
                trajectory["end_time"] = str(times.iloc[-1])
                # Estimate duration (assuming 1 sample per second)
                trajectory["duration_seconds"] = len(times)

            # Store GPS points (sample every 10th point for efficiency)
            points = []
            for i in range(0, len(latitudes), 10):
                points.append(
                    {
                        "lat": latitudes.iloc[i],
                        "lng": longitudes.iloc[i],
                        "speed": speeds.iloc[i] if i < len(speeds) else 0.0,
                        "timestamp": times.iloc[i] if i < len(times) else None,
                    }
                )

            trajectory["points"] = points
            trajectory["total_points"] = len(points)

            return trajectory

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None

    def get_trajectory_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of all processed trajectories.

        Returns:
            Dictionary with summary stats
        """
        if not self.processed_data:
            return {"total_trajectories": 0}

        total_points = sum(t["total_points"] for t in self.processed_data)
        total_distance = sum(t["total_distance_km"] for t in self.processed_data)
        avg_speed = sum(t["average_speed_kmh"] for t in self.processed_data) / len(
            self.processed_data
        )
        max_speed = max(t["max_speed_kmh"] for t in self.processed_data)

        return {
            "total_trajectories": len(self.processed_data),
            "total_gps_points": total_points,
            "total_distance_km": total_distance,
            "average_speed_kmh": avg_speed,
            "max_speed_kmh": max_speed,
            "trajectories": self.processed_data,
        }

    def get_border_crossing_times(self) -> List[Dict[str, Any]]:
        """
        Extract estimated border crossing times from trajectories.

        Returns:
            List of crossing events with timestamps
        """
        crossings = []

        for trajectory in self.processed_data:
            # Simple heuristic: look for periods of low speed near border
            # Placeholder - real implementation needs sophisticated analysis
            border_lat = 31.766  # Approximate border latitude
            border_lng = -106.451

            slow_points = []
            for point in trajectory["points"]:
                if point["speed"] < 5.0:  # km/h
                    distance_to_border = abs(point["lat"] - border_lat) + abs(
                        point["lng"] - border_lng
                    )
                    if distance_to_border < 0.01:  # Within ~1km
                        slow_points.append(point)

            if slow_points:
                # Estimate crossing time as middle of slow period
                mid_point = slow_points[len(slow_points) // 2]
                crossings.append(
                    {
                        "trajectory_id": trajectory["file_name"],
                        "crossing_time": mid_point["timestamp"],
                        "latitude": mid_point["lat"],
                        "longitude": mid_point["lng"],
                        "wait_duration_minutes": (
                            len(slow_points) * 10 / 60  # Rough estimate
                        ),
                    }
                )

        return crossings
