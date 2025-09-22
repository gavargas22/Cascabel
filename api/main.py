"""
Cascabel Simulation API
======================

FastAPI server for multi-queue border crossing simulation with telemetry generation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import uuid
import asyncio
import json

from cascabel.models.waitline import WaitLine
from cascabel.models.simulation import Simulation
from cascabel.models.models import (
    BorderCrossingConfig, SimulationConfig, PhoneConfig,
    SimulationResult, CarState, ServiceNodeState
)
from cascabel.simulation.csv_generator import CSVGenerator

app = FastAPI(
    title="Cascabel Border Crossing Simulation API",
    description="API for simulating car queues at border crossings with realistic telemetry generation",
    version="1.0.0"
)

# In-memory storage for simulations (use Redis/database in production)
simulations = {}


class SimulationRequest(BaseModel):
    """Request to start a simulation."""
    border_config: BorderCrossingConfig
    simulation_config: Optional[SimulationConfig] = None
    phone_config: Optional[PhoneConfig] = None


class SimulationStatus(BaseModel):
    """Status of a running simulation."""
    simulation_id: str
    status: str  # "running", "completed", "failed"
    progress: float
    current_time: float
    total_arrivals: int
    total_completions: int
    message: Optional[str] = None


async def run_simulation(simulation_id: str):
    """
    Run the simulation in the background.
    """
    sim = simulations.get(simulation_id)
    if not sim:
        return

    try:
        simulation = sim["simulation"]

        # Run the simulation (this will block until completion)
        simulation()

        # Update final status
        final_stats = simulation.get_statistics()
        sim["current_time"] = final_stats.simulation_duration
        sim["status"] = "completed"

    except Exception as e:
        sim["status"] = "failed"
        sim["error"] = str(e)


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
        geojson_path = "cascabel/paths/jrz2elp/bota.geojson"
        waitline = WaitLine(geojson_path, {"slow": 0.8, "fast": 0.2}, line_length_seed=1.0)

        # Create simulation with provided configs
        simulation = Simulation(
            waitline=waitline,
            border_config=request.border_config,
            simulation_config=request.simulation_config
        )

        # Store simulation state
        simulations[simulation_id] = {
            "status": "running",
            "simulation": simulation,
            "request": request,
            "start_time": datetime.now(),
            "current_time": 0.0,
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
        raise HTTPException(
            status_code=400,
            detail=f"Failed to start simulation: {str(e)}"
        )


@app.get("/simulation/{simulation_id}/status", response_model=SimulationStatus)
async def get_simulation_status(simulation_id: str):
    """Get the current status of a simulation."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    # Get current statistics from simulation
    try:
        stats = sim["simulation"].get_statistics()
        max_time = sim["request"].simulation_config.max_simulation_time
        progress = min(1.0, sim["current_time"] / max_time)
    except Exception:
        stats = None
        progress = 0.0

    return SimulationStatus(
        simulation_id=simulation_id,
        status=sim["status"],
        progress=progress,
        current_time=sim["current_time"],
        total_arrivals=(stats.execution_stats.total_arrivals
                       if stats else 0),
        total_completions=(stats.execution_stats.total_completions
                          if stats else 0),
        message=sim.get("error")
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


@app.post("/simulation/{simulation_id}/add_car")
async def add_car_to_simulation(simulation_id: str, phone_config: Optional[PhoneConfig] = None):
    """Add a new car to a running simulation."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]
    if sim["status"] != "running":
        raise HTTPException(status_code=400, detail="Simulation is not running")

    try:
        # Add car to simulation
        car, queue_index = sim["simulation"].border_crossing.add_car(
            sampling_rate=phone_config.sampling_rate if phone_config else 10,
            phone_config=phone_config.dict() if phone_config else None
        )

        if car:
            return {
                "car_id": car.car_id,
                "queue_id": queue_index,
                "message": "Car added successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add car (queue full)")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add car: {str(e)}")


@app.put("/simulation/{simulation_id}/service_node/{node_id}")
async def update_service_node_rate(simulation_id: str, node_id: str, rate: float):
    """Update the service rate of a specific service node."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]
    if sim["status"] != "running":
        raise HTTPException(status_code=400, detail="Simulation is not running")

    try:
        # Find and update the service node
        border_crossing = sim["simulation"].border_crossing
        node_found = False

        for node in border_crossing.service_nodes:
            if node.node_id == node_id:
                node.service_rate = rate
                node_found = True
                break

        if not node_found:
            raise HTTPException(status_code=404, detail="Service node not found")

        return {"node_id": node_id, "new_rate": rate, "message": "Service rate updated"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update service rate: {str(e)}")


@app.get("/simulation/{simulation_id}/state")
async def get_simulation_state(simulation_id: str):
    """Get the current state of the simulation for real-time visualization."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    try:
        stats = sim["simulation"].get_statistics()

        # Get car positions and states
        cars = []
        for queue in sim["simulation"].border_crossing.queues:
            for car_id, car in queue.cars.items():
                cars.append({
                    "car_id": car_id,
                    "position": car.position,
                    "velocity": car.velocity,
                    "status": car.status,
                    "queue_id": getattr(car, 'queue_id', None)
                })

        # Get service node states
        service_nodes = []
        for i, queue in enumerate(sim["simulation"].border_crossing.queues):
            for node in queue.service_nodes:
                node_state = node.get_state(i)
                service_nodes.append(node_state.dict())

        return {
            "simulation_id": simulation_id,
            "status": sim["status"],
            "current_time": sim["current_time"],
            "cars": cars,
            "service_nodes": service_nodes,
            "statistics": stats.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get simulation state: {str(e)}")


@app.post("/simulation/{simulation_id}/advance")
async def advance_simulation(simulation_id: str, dt: float = 1.0):
    """Manually advance the simulation by a time step (for testing/debugging)."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]
    if sim["status"] != "running":
        raise HTTPException(status_code=400, detail="Simulation is not running")

    try:
        # Advance simulation time
        completed_cars = sim["simulation"].border_crossing.advance_time(dt)
        sim["current_time"] += dt

        return {
            "advanced_by": dt,
            "completed_cars": len(completed_cars),
            "current_time": sim["current_time"]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to advance simulation: {str(e)}")


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Cascabel Border Crossing Simulation API",
        "version": "1.0.0",
        "docs": "/docs"
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)