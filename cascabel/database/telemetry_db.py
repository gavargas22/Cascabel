"""
SQLite database for storing simulation telemetry data.
"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class TelemetryDatabase:
    """Database for storing phone telemetry data from simulations."""

    def __init__(self, db_path: str = "cascabel_telemetry.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Simulations table - metadata about each simulation run
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                simulation_id TEXT PRIMARY KEY,
                start_time REAL NOT NULL,
                end_time REAL,
                total_cars INTEGER DEFAULT 0,
                total_arrivals INTEGER DEFAULT 0,
                total_completions INTEGER DEFAULT 0,
                average_wait_time REAL,
                border_crossing TEXT,
                geojson_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Telemetry records table - individual sensor readings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                car_id TEXT NOT NULL,
                timestamp REAL NOT NULL,

                -- GPS data
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude REAL,
                gps_accuracy REAL,

                -- Motion data
                speed REAL,
                heading REAL,
                acceleration_x REAL,
                acceleration_y REAL,
                acceleration_z REAL,

                -- Car state
                car_status TEXT,
                queue_id INTEGER,
                position_on_path REAL,

                -- Timing
                arrival_time REAL,
                service_start_time REAL,
                completion_time REAL,
                wait_time REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_simulation
            ON telemetry_records(simulation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_car
            ON telemetry_records(simulation_id, car_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp
            ON telemetry_records(timestamp)
        """)

        self.conn.commit()

    def save_simulation_metadata(
        self,
        simulation_id: str,
        start_time: float,
        end_time: Optional[float] = None,
        total_cars: int = 0,
        total_arrivals: int = 0,
        total_completions: int = 0,
        average_wait_time: Optional[float] = None,
        border_crossing: str = "unknown",
        geojson_path: str = "",
    ):
        """
        Save or update simulation metadata.

        Args:
            simulation_id: Unique simulation identifier
            start_time: Simulation start timestamp
            end_time: Simulation end timestamp (if completed)
            total_cars: Total number of cars spawned
            total_arrivals: Total cars that arrived at queue
            total_completions: Total cars that completed service
            average_wait_time: Average wait time in seconds
            border_crossing: Name of border crossing
            geojson_path: Path to GeoJSON file used
        """
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO simulations
            (simulation_id, start_time, end_time, total_cars, total_arrivals,
             total_completions, average_wait_time, border_crossing, geojson_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                simulation_id,
                start_time,
                end_time,
                total_cars,
                total_arrivals,
                total_completions,
                average_wait_time,
                border_crossing,
                geojson_path,
            ),
        )
        self.conn.commit()

    def save_telemetry_record(
        self,
        simulation_id: str,
        car_id: str,
        timestamp: float,
        latitude: float,
        longitude: float,
        speed: float = 0.0,
        heading: float = 0.0,
        acceleration_x: float = 0.0,
        acceleration_y: float = 0.0,
        acceleration_z: float = 0.0,
        car_status: str = "unknown",
        queue_id: Optional[int] = None,
        position_on_path: float = 0.0,
        arrival_time: Optional[float] = None,
        service_start_time: Optional[float] = None,
        completion_time: Optional[float] = None,
        wait_time: Optional[float] = None,
        altitude: Optional[float] = None,
        gps_accuracy: Optional[float] = None,
    ):
        """
        Save a single telemetry record.

        Args:
            simulation_id: Simulation identifier
            car_id: Car identifier
            timestamp: Record timestamp
            latitude: GPS latitude
            longitude: GPS longitude
            speed: Speed in m/s
            heading: Heading in degrees
            acceleration_x: X-axis acceleration (m/s²)
            acceleration_y: Y-axis acceleration (m/s²)
            acceleration_z: Z-axis acceleration (m/s²)
            car_status: Car status (approaching, queued, serving, completed)
            queue_id: Queue ID if assigned
            position_on_path: Position along path in meters
            arrival_time: Time car arrived at queue
            service_start_time: Time service started
            completion_time: Time service completed
            wait_time: Total wait time in seconds
            altitude: GPS altitude
            gps_accuracy: GPS accuracy in meters
        """
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO telemetry_records
            (simulation_id, car_id, timestamp, latitude, longitude, altitude, gps_accuracy,
             speed, heading, acceleration_x, acceleration_y, acceleration_z,
             car_status, queue_id, position_on_path,
             arrival_time, service_start_time, completion_time, wait_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                simulation_id,
                car_id,
                timestamp,
                latitude,
                longitude,
                altitude,
                gps_accuracy,
                speed,
                heading,
                acceleration_x,
                acceleration_y,
                acceleration_z,
                car_status,
                queue_id,
                position_on_path,
                arrival_time,
                service_start_time,
                completion_time,
                wait_time,
            ),
        )

    def save_telemetry_batch(self, records: List[Dict[str, Any]]):
        """
        Save multiple telemetry records in a batch.

        Args:
            records: List of telemetry record dictionaries
        """
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

        cursor = self.conn.cursor()
        for record in records:
            cursor.execute(
                """
                INSERT INTO telemetry_records
                (simulation_id, car_id, timestamp, latitude, longitude, altitude, gps_accuracy,
                 speed, heading, acceleration_x, acceleration_y, acceleration_z,
                 car_status, queue_id, position_on_path,
                 arrival_time, service_start_time, completion_time, wait_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.get("simulation_id"),
                    record.get("car_id"),
                    record.get("timestamp"),
                    record.get("latitude"),
                    record.get("longitude"),
                    record.get("altitude"),
                    record.get("gps_accuracy"),
                    record.get("speed"),
                    record.get("heading"),
                    record.get("acceleration_x"),
                    record.get("acceleration_y"),
                    record.get("acceleration_z"),
                    record.get("car_status"),
                    record.get("queue_id"),
                    record.get("position_on_path"),
                    record.get("arrival_time"),
                    record.get("service_start_time"),
                    record.get("completion_time"),
                    record.get("wait_time"),
                ),
            )
        self.conn.commit()

    def get_simulation_records(self, simulation_id: str) -> List[Dict[str, Any]]:
        """
        Get all telemetry records for a simulation.

        Args:
            simulation_id: Simulation identifier

        Returns:
            List of telemetry record dictionaries
        """
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM telemetry_records
            WHERE simulation_id = ?
            ORDER BY timestamp ASC
        """,
            (simulation_id,),
        )

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
