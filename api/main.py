"""
Cascabel Simulation API
======================

FastAPI server for car queue simulation with telemetry generation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid
import asyncio

from cascabel.models.waitline import WaitLine
from cascabel.models.car import Car
from cascabel.models.queuing.mm1_queue import MM1Queue
from cascabel.simulation.telemetry.telemetry_generator import TelemetryGenerator
from cascabel.simulation.csv_generator import CSVGenerator

app = FastAPI(
    title="Cascabel Border Crossing Simulation API",
    description="API for simulating car queues at border crossings with realistic telemetry generation",
    version="1.0.0"
)

# In-memory storage for simulations (use Redis/database in production)
simulations = {}


class QueueConfig(BaseModel):
    path: str = "jrz2elp/bota"
    arrival_rate: float = 0.5  # cars per minute
    service_rate: float = 0.8  # cars per minute
    max_queue_length: int = 20


class PhoneConfig(BaseModel):
    sampling_rate: int = 10  # Hz
    gps_noise: Dict[str, float] = {"horizontal_accuracy": 5.0, "vertical_accuracy": 3.0}
    accelerometer_noise: float = 0.01  # m/s²
    gyro_noise: float = 0.001  # rad/s
    device_orientation: str = "portrait"


class SimulationConfig(BaseModel):
    duration: int = 3600  # seconds
    realtime: bool = True


class SimulationRequest(BaseModel):
    queue_config: QueueConfig
    phone_config: PhoneConfig
    simulation_config: SimulationConfig


class SimulationStatus(BaseModel):
    simulation_id: str
    status: str  # "running", "completed", "failed"
    progress: float
    cars_processed: int
    current_queue_length: int
    start_time: Optional[datetime]
    estimated_completion: Optional[datetime]
    error_message: Optional[str] = None


@app.post("/simulate", response_model=Dict[str, str])
async def start_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """
    Start a new simulation run.

    Returns simulation ID and WebSocket URL for realtime streaming.
    """
    simulation_id = str(uuid.uuid4())

    # Initialize simulation
    try:
        # Create waitline
        geojson_path = f"cascabel/paths/{request.queue_config.path}.geojson"
        waitline = WaitLine(geojson_path, {"slow": 0.8, "fast": 0.2}, line_length_seed=1.0)

        # Create queue
        queue = MM1Queue(
            arrival_rate=request.queue_config.arrival_rate,
            service_rate=request.queue_config.service_rate,
            max_queue_length=request.queue_config.max_queue_length
        )

        # Create telemetry generator
        telemetry_gen = TelemetryGenerator(waitline, request.phone_config.__dict__)

        # Store simulation state
        simulations[simulation_id] = {
            "status": "running",
            "request": request,
            "waitline": waitline,
            "queue": queue,
            "telemetry_gen": telemetry_gen,
            "start_time": datetime.now(),
            "progress": 0.0,
            "cars_processed": 0,
            "telemetry_data": [],
            "error": None
        }

        # Start background simulation
        background_tasks.add_task(run_simulation, simulation_id)

        return {
            "simulation_id": simulation_id,
            "status": "running",
            "websocket_url": f"ws://localhost:8000/ws/{simulation_id}",
            "message": "Simulation started successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start simulation: {str(e)}")


@app.get("/simulation/{simulation_id}/status", response_model=SimulationStatus)
async def get_simulation_status(simulation_id: str):
    """Get the current status of a simulation."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    # Calculate estimated completion
    if sim["status"] == "running":
        total_duration = sim["request"].simulation_config.duration
        estimated_completion = sim["start_time"] + timedelta(seconds=total_duration)
    else:
        estimated_completion = None

    return SimulationStatus(
        simulation_id=simulation_id,
        status=sim["status"],
        progress=sim["progress"],
        cars_processed=sim["cars_processed"],
        current_queue_length=sim["queue"].queue_length if "queue" in sim else 0,
        start_time=sim["start_time"],
        estimated_completion=estimated_completion,
        error_message=sim.get("error")
    )


@app.get("/simulation/{simulation_id}/telemetry")
async def get_simulation_telemetry(simulation_id: str, format: str = "csv"):
    """
    Get telemetry data as CSV.

    For running simulations, returns data collected so far.
    For completed simulations, returns all data.
    """
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    if not sim["telemetry_data"]:
        raise HTTPException(status_code=404, detail="No telemetry data available yet")

    csv_gen = CSVGenerator()
    csv_content = csv_gen.generate_csv(sim["telemetry_data"])

    if format == "json":
        # Convert CSV to JSON (simplified)
        return {"telemetry": sim["telemetry_data"]}
    else:
        # Return as CSV file
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=simulation_{simulation_id}.csv"}
        )


@app.get("/simulations")
async def list_simulations(status: Optional[str] = None, limit: int = 50):
    """List all simulations with optional filtering."""
    sim_list = []
    for sim_id, sim in simulations.items():
        if status and sim["status"] != status:
            continue

        sim_list.append({
            "simulation_id": sim_id,
            "status": sim["status"],
            "start_time": sim["start_time"],
            "cars_processed": sim["cars_processed"],
            "config": sim["request"].dict()
        })

        if len(sim_list) >= limit:
            break

    return {"simulations": sim_list, "total": len(simulations)}


@app.delete("/simulation/{simulation_id}")
async def cancel_simulation(simulation_id: str):
    """Cancel a running simulation or delete completed simulation data."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    if sim["status"] == "running":
        sim["status"] = "cancelled"
        sim["error"] = "Cancelled by user"
    else:
        # Delete completed simulation
        del simulations[simulation_id]

    return {"simulation_id": simulation_id, "status": "cancelled"}


async def run_simulation(simulation_id: str):
    """
    Run the simulation in the background.

    This is a simplified version. In production, this would be more sophisticated
    with proper async handling and progress updates.
    """
    sim = simulations.get(simulation_id)
    if not sim:
        return

    try:
        request = sim["request"]
        queue = sim["queue"]
        telemetry_gen = sim["telemetry_gen"]

        # Generate car arrivals
        arrival_times = queue.arrival_process.generate_arrival_times(
            request.simulation_config.duration / 60,  # Convert to minutes
            sim["start_time"]
        )

        total_cars = len(arrival_times)
        sim["telemetry_data"] = []

        for i, arrival_time in enumerate(arrival_times):
            # Create car
            car = Car(f"car_{i}", request.phone_config.sampling_rate, request.phone_config.__dict__)

            # Add to queue
            if queue.add_car(car, arrival_time):
                # Simulate car movement and generate telemetry
                telemetry_records = telemetry_gen.generate_telemetry_for_car(
                    car, arrival_time, 300  # 5 minutes of data per car
                )
                sim["telemetry_data"].extend(telemetry_records)

            # Update progress
            sim["progress"] = (i + 1) / total_cars
            sim["cars_processed"] = i + 1

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)

        sim["status"] = "completed"

    except Exception as e:
        sim["status"] = "failed"
        sim["error"] = str(e)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Cascabel Border Crossing Simulation API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)