"""
Simulation API Router
====================

FastAPI router for border crossing simulation endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional
import uuid
from datetime import datetime

from cascabel.models.waitline import WaitLine
from cascabel.models.border_crossing import ServiceNode
from cascabel.models.simulation import Simulation
from cascabel.models.models import BorderCrossingConfig, SimulationConfig, PhoneConfig
from cascabel.simulation.csv_generator import CSVGenerator
from cascabel.utils.geojson_loader import GeoJSONLoader
from cascabel.utils.bounding_validator import constrain_point_to_bounds
from ..shared import simulations, websockets

router = APIRouter()


class SimulationRequest(BaseModel):
    """Request to start a simulation."""

    border_config: BorderCrossingConfig
    simulation_config: Optional[SimulationConfig] = None
    phone_config: Optional[PhoneConfig] = None
    geojson_path: str = "cascabel/paths/usa2mx/bota.geojson"


class SimulationStatus(BaseModel):
    """Status of a running simulation."""

    simulation_id: str
    status: str  # "running", "completed", "failed"
    progress: float
    current_time: float
    total_arrivals: int
    total_completions: int
    message: Optional[str] = None


class UpdateRate(BaseModel):
    rate: float


class TimeSpeedUpdate(BaseModel):
    time_factor: float


async def run_simulation(simulation_id: str):
    """
    Run the simulation in the background with real-time WebSocket updates.
    """
    sim = simulations.get(simulation_id)
    if not sim:
        return

    simulation = sim["simulation"]
    try:
        print("executing multi-queue border crossing simulation...")
        simulation.simulation_state["running"] = True

        while simulation.simulation_state["running"]:
            dt = simulation.advance_time()
            simulation.border_crossing.advance_time(dt)
            if not simulation.should_continue():
                simulation.simulation_state["running"] = False
            simulation.record_positions()

            # Send real-time update
            # Collect car data
            cars_data = []
            for queue in simulation.border_crossing.queues:
                for car in queue.cars.values():
                    # Get GPS position along waitline
                    position_point = (
                        simulation.waitline.compute_position_at_distance_from_start(
                            car.position
                        )
                    )
                    if position_point and simulation.bounds_polygon:
                        # Constrain position to bounds
                        position_point = constrain_point_to_bounds(
                            position_point, simulation.bounds_polygon
                        )

                    # Convert UTM to lat/lon coordinates
                    if position_point:
                        position_coords = simulation.waitline.utm_to_latlon(
                            position_point
                        )
                    else:
                        position_coords = [0, 0]

                    car_data = {
                        "id": str(car.car_id),
                        "position": position_coords,
                        "status": car.status,
                        "velocity": car.velocity,
                        "acceleration": car.acceleration,
                        "queue_id": car.queue_id,
                        "arrival_time": car.arrival_time,
                        "service_start_time": car.service_start_time,
                        "completion_time": car.completion_time,
                        "distance_traveled": car.position,
                    }
                    cars_data.append(car_data)

            # Collect queue data
            queues_data = []
            for i, queue in enumerate(simulation.border_crossing.queues):
                throughput = len([node for node in queue.service_nodes if node.is_busy])
                queues_data.append(
                    {"length": len(queue.car_positions), "throughput": throughput}
                )

            # Calculate average wait time
            completed_cars = [
                car
                for queue in simulation.border_crossing.queues
                for car in queue.cars.values()
                if (
                    car.status == "completed"
                    and car.service_start_time
                    and car.arrival_time
                )
            ]
            avg_wait_time = None
            if completed_cars:
                total_wait = sum(
                    car.service_start_time - car.arrival_time for car in completed_cars
                )
                avg_wait_time = total_wait / len(completed_cars)

            message = {
                "type": "simulation_update",
                "data": {
                    "cars": cars_data,
                    "queues": queues_data,
                    "metrics": {
                        "total_arrivals": simulation.border_crossing.total_arrivals,
                        "total_completions": simulation.border_crossing.total_completions,
                        "average_wait_time": avg_wait_time,
                    },
                },
            }

            if simulation_id in websockets:
                for ws in websockets[simulation_id]:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass

            # Small delay to prevent flooding
            import asyncio

            await asyncio.sleep(0.1)

        # Collect telemetry data
        if hasattr(simulation, "telemetry_data"):
            sim["telemetry_data"] = simulation.telemetry_data

        # Update final status
        final_stats = simulation.get_statistics()
        sim["current_time"] = final_stats.simulation_duration
        sim["status"] = "completed"

        final_status = {
            "simulation_id": simulation_id,
            "status": "completed",
            "progress": 1.0,
            "current_time": final_stats.simulation_duration,
            "total_arrivals": final_stats.total_arrivals,
            "total_completions": final_stats.total_completions,
            "message": "Simulation completed",
        }
        if simulation_id in websockets:
            for ws in websockets[simulation_id]:
                try:
                    await ws.send_json(final_status)
                except Exception:
                    pass

    except Exception as e:
        sim["status"] = "failed"
        sim["error"] = str(e)
        error_status = {
            "simulation_id": simulation_id,
            "status": "failed",
            "progress": 0.0,
            "current_time": 0.0,
            "total_arrivals": 0,
            "total_completions": 0,
            "message": str(e),
        }
        if simulation_id in websockets:
            for ws in websockets[simulation_id]:
                try:
                    await ws.send_json(error_status)
                except Exception:
                    pass


@router.post("/simulate", response_model=Dict[str, str])
async def start_simulation(
    request: SimulationRequest, background_tasks: BackgroundTasks
):
    """
    Start a new simulation run.

    Returns simulation ID and WebSocket URL for realtime streaming.
    """
    simulation_id = str(uuid.uuid4())

    # Initialize simulation
    try:
        # Create waitline
        waitline = WaitLine(
            request.geojson_path, {"slow": 0.8, "fast": 0.2}, line_length_seed=1.0
        )

        # Create simulation with provided configs
        simulation = Simulation(
            waitline=waitline,
            border_config=request.border_config,
            simulation_config=request.simulation_config,
            phone_config=request.phone_config,
        )

        # Store simulation state
        simulations[simulation_id] = {
            "status": "running",
            "simulation": simulation,
            "request": request,
            "start_time": datetime.now(),
            "current_time": 0.0,
            "telemetry_data": [],
            "cars_processed": 0,
            "error": None,
        }

        # Start background simulation
        background_tasks.add_task(run_simulation, simulation_id)

        return {
            "simulation_id": simulation_id,
            "status": "running",
            "websocket_url": f"ws://localhost:8000/ws/{simulation_id}",
            "message": "Simulation started successfully",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to start simulation: {str(e)}"
        )


@router.post("/grand-simulate", response_model=Dict[str, str])
async def start_grand_simulation(
    request: SimulationRequest, background_tasks: BackgroundTasks
):
    """
    Start a 24-hour grand simulation run.

    Returns simulation ID and WebSocket URL for realtime streaming.
    """
    if request.simulation_config is None:
        request.simulation_config = SimulationConfig(
            max_simulation_time=86400.0,  # 24 hours
            time_factor=1.0,
            enable_telemetry=True,
            enable_position_tracking=True,
        )
    else:
        # Ensure 24-hour duration
        request.simulation_config.max_simulation_time = 86400.0

    simulation_id = str(uuid.uuid4())

    # Initialize simulation
    try:
        # Create waitline
        waitline = WaitLine(
            request.geojson_path, {"slow": 0.8, "fast": 0.2}, line_length_seed=1.0
        )

        # Create simulation with provided configs
        simulation = Simulation(
            waitline=waitline,
            border_config=request.border_config,
            simulation_config=request.simulation_config,
            phone_config=request.phone_config,
        )

        # Store simulation state
        simulations[simulation_id] = {
            "status": "running",
            "simulation": simulation,
            "request": request,
            "start_time": datetime.now(),
            "current_time": 0.0,
            "telemetry_data": [],
            "cars_processed": 0,
            "error": None,
        }

        # Start background simulation
        background_tasks.add_task(run_simulation, simulation_id)

        return {
            "simulation_id": simulation_id,
            "status": "running",
            "websocket_url": f"ws://localhost:8000/ws/{simulation_id}",
            "message": "Grand simulation started successfully",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to start grand simulation: {str(e)}"
        )


@router.get("/simulation/{simulation_id}/status", response_model=SimulationStatus)
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
        total_arrivals=(stats.execution_stats.total_arrivals if stats else 0),
        total_completions=(stats.execution_stats.total_completions if stats else 0),
        message=sim.get("error"),
    )


@router.get("/simulation/{simulation_id}/telemetry")
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
        # For running simulations, collect any available telemetry data
        if sim["status"] == "running" and "simulation" in sim:
            simulation = sim["simulation"]
            if hasattr(simulation, "telemetry_data") and simulation.telemetry_data:
                sim["telemetry_data"] = simulation.telemetry_data

        # If still no data, return empty CSV with headers
        if not sim["telemetry_data"]:
            csv_gen = CSVGenerator()
            # Return CSV with just headers
            empty_data = [
                {
                    "timestamp": 0.0,
                    "car_id": 0,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "altitude": 0.0,
                    "speed": 0.0,
                    "heading": 0.0,
                    "accelerometer_x": 0.0,
                    "accelerometer_y": 0.0,
                    "accelerometer_z": 0.0,
                    "gyroscope_x": 0.0,
                    "gyroscope_y": 0.0,
                    "gyroscope_z": 0.0,
                }
            ]
            csv_content = csv_gen.generate_csv(empty_data)

            if format == "json":
                return {"telemetry": [], "message": "No telemetry data available yet"}
            else:
                return StreamingResponse(
                    iter([csv_content]),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": (
                            f"attachment; filename=simulation_{simulation_id}_empty.csv"
                        )
                    },
                )

    # Validate telemetry data
    validated_data = []
    for record in sim["telemetry_data"]:
        try:
            # Basic validation
            if not isinstance(record, dict):
                continue
            if "locationLatitude" not in record or "locationLongitude" not in record:
                continue
            lat = record.get("locationLatitude", 0)
            lon = record.get("locationLongitude", 0)
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                continue

            validated_data.append(record)
        except (TypeError, ValueError):
            continue  # Skip invalid records

    if not validated_data:
        raise HTTPException(status_code=500, detail="No valid telemetry data found")

    csv_gen = CSVGenerator()
    csv_content = csv_gen.generate_csv(validated_data)

    if format == "json":
        # Convert to simplified JSON format for frontend
        simplified_data = []
        for record in validated_data:
            simplified_data.append(
                {
                    "timestamp": record.get("loggingTime", ""),
                    "car_id": str(record.get("identifierForVendor", "unknown")),
                    "latitude": record.get("locationLatitude", 0),
                    "longitude": record.get("locationLongitude", 0),
                    "velocity": record.get("locationSpeed", 0),
                    "status": "arriving",  # Default status
                    "queue_id": None,
                }
            )
        return {"telemetry": simplified_data}
    else:
        # Return as CSV file
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=simulation_{simulation_id}.csv"
            },
        )


@router.get("/simulations")
async def list_simulations(status: Optional[str] = None, limit: int = 50):
    """List all simulations with optional filtering."""
    sim_list = []
    for sim_id, sim in simulations.items():
        if status and sim["status"] != status:
            continue

        sim_list.append(
            {
                "simulation_id": sim_id,
                "status": sim["status"],
                "start_time": sim["start_time"],
                "cars_processed": sim["cars_processed"],
                "config": sim["request"].model_dump(),
            }
        )

        if len(sim_list) >= limit:
            break

    return {"simulations": sim_list, "total": len(simulations)}


@router.delete("/simulation/{simulation_id}")
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


@router.post("/simulation/{simulation_id}/add_car")
async def add_car_to_simulation(
    simulation_id: str, phone_config: Optional[PhoneConfig] = None
):
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
            phone_config=phone_config.dict() if phone_config else None,
        )

        if car:
            return {
                "car_id": car.car_id,
                "queue_id": queue_index,
                "message": "Car added successfully",
            }
        else:
            raise HTTPException(
                status_code=400, detail="Failed to add car (queue full)"
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add car: {str(e)}")


@router.put("/simulation/{simulation_id}/service_node/{node_id}")
async def update_service_node_rate(
    simulation_id: str, node_id: str, update: UpdateRate
):
    """Update the service rate of a specific service node."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    try:
        # Find and update the service node
        border_crossing = sim["simulation"].border_crossing
        node_found = False

        for queue in border_crossing.queues:
            for node in queue.service_nodes:
                if node.node_id == node_id:
                    node.service_rate = update.rate
                    node_found = True
                    break
            if node_found:
                break

        if not node_found:
            raise HTTPException(status_code=404, detail="Service node not found")

        return {
            "node_id": node_id,
            "new_rate": update.rate,
            "message": "Service rate updated",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to update service rate: {str(e)}"
        )


@router.get("/simulation/{simulation_id}/state")
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
                queue_id_val = getattr(car, "queue_id", None)
                cars.append(
                    {
                        "car_id": int(car.car_id),
                        "position": car.position,
                        "velocity": car.velocity,
                        "status": car.status,
                        "queue_id": (
                            int(queue_id_val) if queue_id_val is not None else None
                        ),
                    }
                )

        # Get service node states
        service_nodes = []
        for i, queue in enumerate(sim["simulation"].border_crossing.queues):
            for node in queue.service_nodes:
                node_state = node.get_state(i)
                service_nodes.append(node_state.model_dump())

        return {
            "simulation_id": simulation_id,
            "status": sim["status"],
            "current_time": sim["current_time"],
            "cars": cars,
            "service_nodes": service_nodes,
            "statistics": stats.model_dump(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get simulation state: {str(e)}"
        )


@router.post("/simulation/{simulation_id}/advance")
async def advance_simulation(simulation_id: str, dt: float = 1.0):
    """Manually advance the simulation by a time step."""
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
            "current_time": sim["current_time"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to advance simulation: {str(e)}"
        )


@router.get("/simulation/{simulation_id}/visualization-data")
async def get_visualization_data(simulation_id: str, timestamp: Optional[float] = None):
    """
    Fetch batched data for React visualization.

    Returns car positions, queue states, and map data.
    """
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    try:
        stats = sim["simulation"].get_statistics()

        # Get car positions and states
        cars = []
        for queue in sim["simulation"].border_crossing.queues:
            for car_id, car in queue.cars.items():
                queue_id_val = getattr(car, "queue_id", None)
                cars.append(
                    {
                        "car_id": int(car.car_id),
                        "position": car.position,
                        "velocity": car.velocity,
                        "status": car.status,
                        "queue_id": (
                            int(queue_id_val) if queue_id_val is not None else None
                        ),
                    }
                )

        # Get service node states
        service_nodes = []
        for i, queue in enumerate(sim["simulation"].border_crossing.queues):
            for node in queue.service_nodes:
                node_state = node.get_state(i)
                service_nodes.append(node_state.model_dump())

        # If timestamp provided, filter data for that time (simplified)
        # For now, return current state
        data = {
            "simulation_id": simulation_id,
            "timestamp": sim["current_time"],
            "cars": cars,
            "service_nodes": service_nodes,
            "statistics": stats.model_dump(),
        }

        return data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get visualization data: {str(e)}"
        )


@router.put("/simulation/{simulation_id}/time_speed")
async def update_time_speed(simulation_id: str, update: TimeSpeedUpdate):
    """Update the simulation time speed multiplier."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_data = simulations[simulation_id]
    sim_data["simulation"].simulation_config.time_factor = update.time_factor
    sim_data["simulation"].simulation_state["time_factor"] = update.time_factor

    return {"status": "updated", "time_factor": update.time_factor}


@router.post("/simulation/{simulation_id}/add_station")
async def add_service_station(simulation_id: str, queue_id: int = Query(0)):
    """Add a new service station to the specified queue."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_data = simulations[simulation_id]
    border_crossing = sim_data["simulation"].border_crossing

    # Add new service node to the specified queue
    if queue_id >= len(border_crossing.queues):
        raise HTTPException(status_code=400, detail="Invalid queue ID")

    queue = border_crossing.queues[queue_id]

    # Create new service node
    node_id = f"q{queue_id}_n{len(queue.service_nodes)}"
    service_rate = 3.0  # Default service rate
    new_node = ServiceNode(node_id, service_rate)

    # Add to queue and border crossing
    queue.service_nodes.append(new_node)
    border_crossing.service_nodes.append(new_node)

    return {"station_id": node_id, "queue_id": queue_id, "service_rate": service_rate}


@router.websocket("/ws/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    # Allow connections from frontend
    allowed_origins = ["http://localhost:3000"]
    origin = websocket.headers.get("origin")
    if origin not in allowed_origins:
        await websocket.close(code=1008)  # Policy violation
        return
    await websocket.accept()
    if simulation_id not in websockets:
        websockets[simulation_id] = []
    websockets[simulation_id].append(websocket)
    try:
        while True:
            # Keep connection alive, updates sent from run_simulation
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        if simulation_id in websockets and websocket in websockets[simulation_id]:
            websockets[simulation_id].remove(websocket)


# Global variable to store loaded GeoJSON data
loaded_geojson = {}


@router.get("/border-crossings")
async def get_border_crossings():
    """Get list of available border crossing GeoJSON files."""
    import os

    crossings = []

    # Scan for geojson files in paths
    for root, dirs, files in os.walk("cascabel/paths"):
        for file in files:
            if file.endswith(".geojson"):
                # Extract crossing info from path
                # Use os.path operations for cross-platform compatibility
                rel_path = os.path.relpath(root, "cascabel/paths")
                parts = rel_path.split(os.sep)
                if len(parts) >= 1:
                    direction = parts[0]  # mx2usa, usa2mx, etc.
                    crossing_id = file.replace(".geojson", "")
                    name = f"{crossing_id} ({direction})".replace("_", " ").title()

                    crossings.append(
                        {"id": crossing_id, "name": name, "direction": direction}
                    )

    return {"crossings": crossings}


@router.post("/border-crossings/{crossing_id}/load")
async def load_border_crossing(crossing_id: str):
    """Load and validate a specific border crossing GeoJSON file."""
    import os

    # Find the geojson file
    geojson_path = None
    for root, dirs, files in os.walk("cascabel/paths"):
        for file in files:
            if file == f"{crossing_id}.geojson":
                geojson_path = os.path.join(root, file)
                break
        if geojson_path:
            break

    if not geojson_path:
        raise HTTPException(status_code=404, detail="Border crossing not found")

    try:
        loader = GeoJSONLoader(geojson_path)
        # Store in global cache
        loaded_geojson[crossing_id] = loader

        return {
            "status": "loaded",
            "polygon_bounds": loader.polygon_utm.wkt,
            "start_point": [loader.start_point_utm.x, loader.start_point_utm.y],
            "stop_point": [loader.stop_point_utm.x, loader.stop_point_utm.y],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid GeoJSON: {str(e)}")


@router.get("/simulations/config")
async def get_simulation_config():
    """Get current simulation configuration including loaded boundary info."""
    config = {"available_geojson": list(loaded_geojson.keys()), "bounds": {}}

    # Include loaded boundary information
    for crossing_id, loader in loaded_geojson.items():
        config["bounds"][crossing_id] = {
            "utm_epsg": loader.utm_epsg_code,
            "polygon_wkt": loader.polygon_utm.wkt,
            "start_point": [loader.start_point_utm.x, loader.start_point_utm.y],
            "stop_point": [loader.stop_point_utm.x, loader.stop_point_utm.y],
        }

    return config


@router.get("/geojson/{path_name}")
async def get_geojson(path_name: str):
    """
    Get GeoJSON data for border crossing paths.

    Args:
        path_name: Name of the path (e.g., "usa2mx/bota")

    Returns:
        GeoJSON FeatureCollection
    """
    import json
    import os

    # Construct absolute path to the GeoJSON file
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    geojson_path = os.path.join(root_dir, "cascabel", "paths", f"{path_name}.geojson")

    print(f"DEBUG: Root dir = {root_dir}")
    print(f"DEBUG: Looking for file at: {geojson_path}")
    print(f"DEBUG: File exists: {os.path.exists(geojson_path)}")

    if not os.path.exists(geojson_path):
        raise HTTPException(
            status_code=404, detail=f"GeoJSON file not found: {path_name}"
        )

    try:
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)
        return geojson_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading GeoJSON: {str(e)}")
