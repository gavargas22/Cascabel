"""
Pydantic Models for Cascabel Border Crossing Simulation
======================================================

Comprehensive data models using Pydantic for validation, serialization,
and configuration management.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
import numpy as np


# Configuration Models
class PhoneConfig(BaseModel):
    """Configuration for mobile device sensor simulation."""
    sampling_rate: float = Field(10.0, description="Sensor sampling rate in Hz")
    gps_noise: Dict[str, float] = Field(
        default_factory=lambda: {"horizontal_accuracy": 5.0,
                                "vertical_accuracy": 3.0}
    )
    accelerometer_noise: float = Field(0.01,
                                      description="Accelerometer noise std dev")
    gyro_noise: float = Field(0.001, description="Gyroscope noise std dev")
    device_orientation: Literal["portrait", "landscape"] = "portrait"


class BorderCrossingConfig(BaseModel):
    """Configuration for border crossing layout and parameters."""
    num_queues: int = Field(3, ge=1, description="Number of queues/lanes")
    nodes_per_queue: List[int] = Field(
        default_factory=lambda: [2, 3, 2],
        description="Number of service nodes per queue"
    )
    arrival_rate: float = Field(6.0, gt=0, description="Overall arrival rate (cars/minute)")
    service_rates: List[float] = Field(
        default_factory=lambda: [3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9],
        description="Service rates for each node (cars/minute)"
    )
    queue_assignment: Literal["random", "shortest", "round_robin"] = "shortest"
    safe_distance: float = Field(8.0, gt=0, description="Safe distance between cars (meters)")
    max_queue_length: int = Field(50, ge=1, description="Maximum cars per queue")

    @validator('nodes_per_queue')
    def validate_nodes_per_queue(cls, v, values):
        if 'num_queues' in values and len(v) != values['num_queues']:
            raise ValueError('nodes_per_queue length must match num_queues')
        return v

    @validator('service_rates')
    def validate_service_rates(cls, v, values):
        if 'nodes_per_queue' in values:
            expected_length = sum(values['nodes_per_queue'])
            if len(v) != expected_length:
                raise ValueError(f'service_rates length must match total nodes ({expected_length})')
        return v


class SimulationConfig(BaseModel):
    """Configuration for simulation execution."""
    max_simulation_time: float = Field(3600.0, gt=0, description="Maximum simulation time (seconds)")
    time_factor: float = Field(1.0, description="Time acceleration factor")
    enable_telemetry: bool = Field(True, description="Generate telemetry data")
    enable_position_tracking: bool = Field(True, description="Track car positions")


# State Models
class CarState(BaseModel):
    """Current state of a car in the simulation."""
    car_id: int
    position: float = Field(..., description="Position along queue (meters)")
    velocity: float = Field(..., description="Current velocity (m/s)")
    acceleration: float = Field(..., description="Current acceleration (m/s²)")
    status: Literal["arriving", "queued", "serving", "completed"] = "arriving"
    queue_id: Optional[int] = Field(None, description="Assigned queue ID")
    arrival_time: Optional[float] = None
    service_start_time: Optional[float] = None
    completion_time: Optional[float] = None

    @property
    def waiting_time(self) -> Optional[float]:
        """Calculate waiting time in queue."""
        if self.service_start_time and self.arrival_time:
            return self.service_start_time - self.arrival_time
        return None

    @property
    def service_time(self) -> Optional[float]:
        """Calculate service time."""
        if self.completion_time and self.service_start_time:
            return self.completion_time - self.service_start_time
        return None


class ServiceNodeState(BaseModel):
    """Current state of a service node."""
    node_id: str
    queue_id: int
    is_busy: bool = False
    current_car_id: Optional[int] = None
    service_rate: float
    total_served: int = 0
    total_service_time: float = 0.0

    @property
    def utilization(self) -> float:
        """Calculate utilization based on served cars and time."""
        if self.total_service_time == 0:
            return 0.0
        # Assuming average service time per car
        expected_total_time = self.total_served / (self.service_rate / 60)  # Convert to seconds
        return min(1.0, self.total_service_time / expected_total_time) if expected_total_time > 0 else 0.0


class QueueState(BaseModel):
    """Current state of a queue."""
    queue_id: int
    total_cars: int = 0
    queue_length: int = 0  # Cars waiting to be served
    busy_nodes: int = 0
    num_service_nodes: int
    total_arrivals: int = 0
    total_completions: int = 0

    @property
    def utilization(self) -> float:
        """Calculate queue utilization."""
        return self.busy_nodes / self.num_service_nodes if self.num_service_nodes > 0 else 0.0


# Telemetry Models
class GPSData(BaseModel):
    """GPS sensor data."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    horizontal_accuracy: Optional[float] = None
    vertical_accuracy: Optional[float] = None
    timestamp: float


class AccelerometerData(BaseModel):
    """Accelerometer sensor data."""
    x: float
    y: float
    z: float
    timestamp: float


class GyroscopeData(BaseModel):
    """Gyroscope sensor data."""
    x: float
    y: float
    z: float
    timestamp: float


class MotionData(BaseModel):
    """Device motion data."""
    yaw: float
    roll: float
    pitch: float
    rotation_rate_x: float
    rotation_rate_y: float
    rotation_rate_z: float
    attitude_quaternion: List[float]  # [w, x, y, z]
    timestamp: float


class ActivityData(BaseModel):
    """Activity recognition data."""
    activity: str = "automotive"
    confidence: float = 1.0
    timestamp: float


class TelemetryRecord(BaseModel):
    """Complete telemetry record matching mobile device format."""
    timestamp: float
    car_id: int
    gps: GPSData
    accelerometer: AccelerometerData
    gyroscope: GyroscopeData
    motion: MotionData
    activity: ActivityData
    device_info: Dict[str, Any] = Field(default_factory=dict)


# Result Models
class BorderCrossingStats(BaseModel):
    """Statistics for border crossing performance."""
    total_arrivals: int
    total_completions: int
    current_time: float
    num_queues: int
    total_service_nodes: int
    queue_assignment_strategy: str
    overall_utilization: float
    average_waiting_time: Optional[float] = None
    average_service_time: Optional[float] = None
    throughput: float  # cars per minute

    @validator('throughput', pre=True, always=True)
    def calculate_throughput(cls, v, values):
        if 'total_completions' in values and 'current_time' in values:
            time_minutes = values['current_time'] / 60
            return values['total_completions'] / time_minutes if time_minutes > 0 else 0.0
        return 0.0


class QueueStats(BaseModel):
    """Detailed statistics for a single queue."""
    queue_id: int
    total_cars: int
    queue_length: int
    busy_nodes: int
    num_service_nodes: int
    utilization: float
    average_wait_time: float = 0.0
    total_arrivals: int
    total_completions: int


class ServiceNodeStats(BaseModel):
    """Detailed statistics for a service node."""
    node_id: str
    queue_id: int
    service_rate: float
    total_served: int
    total_service_time: float
    utilization: float
    average_service_time: float = 0.0


class SimulationResult(BaseModel):
    """Complete simulation results."""
    simulation_config: SimulationConfig
    border_config: BorderCrossingConfig
    execution_stats: BorderCrossingStats
    queue_stats: List[QueueStats]
    node_stats: List[ServiceNodeStats]
    total_positions_recorded: int
    total_telemetry_records: int
    simulation_duration: float
    completed_at: datetime = Field(default_factory=datetime.now)


# API Models
class SimulationRequest(BaseModel):
    """Request to start a simulation."""
    border_config: BorderCrossingConfig
    simulation_config: Optional[SimulationConfig] = None
    phone_config: Optional[PhoneConfig] = None


class SimulationStatus(BaseModel):
    """Status of a running simulation."""
    simulation_id: str
    status: Literal["running", "completed", "failed"]
    progress: float = Field(0.0, ge=0.0, le=1.0)
    current_time: float
    total_arrivals: int
    total_completions: int
    message: Optional[str] = None


class SimulationResponse(BaseModel):
    """Response from simulation creation."""
    simulation_id: str
    status: str
    estimated_duration: Optional[float] = None


# Validation helpers
def validate_border_config(config: Dict[str, Any]) -> BorderCrossingConfig:
    """Validate and create BorderCrossingConfig from dictionary."""
    return BorderCrossingConfig(**config)


def validate_simulation_config(config: Dict[str, Any]) -> SimulationConfig:
    """Validate and create SimulationConfig from dictionary."""
    return SimulationConfig(**config)


def validate_phone_config(config: Dict[str, Any]) -> PhoneConfig:
    """Validate and create PhoneConfig from dictionary."""
    return PhoneConfig(**config)