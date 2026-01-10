"""
Simulation API Router
====================

FastAPI router for border crossing simulation endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import uuid
from datetime import datetime
import os
import json
import asyncio
import traceback
import random
from pathlib import Path

from cascabel.models.waitline import WaitLine
from cascabel.models.border_crossing import ServiceNode
from cascabel.models.simulation import Simulation
from cascabel.models.models import BorderCrossingConfig, SimulationConfig, PhoneConfig
from cascabel.simulation.csv_generator import CSVGenerator
from cascabel.utils.geojson_loader import GeoJSONLoader
from cascabel.utils.bounding_validator import constrain_point_to_bounds
from cascabel.database import TelemetryDatabase
from ..shared import simulations, websockets

router = APIRouter()


class PhysicsConfig(BaseModel):
    """Physics simulation parameters."""
    min_speed_mps: float = 12.1  # 27 mph
    max_speed_mps: float = 14.7  # 33 mph
    safe_distance_meters: float = 3.0
    max_acceleration: float = 0.75
    max_deceleration: float = 1.25


class PhysicsRanges(BaseModel):
    """Ranges for random selection of physics parameters."""
    speed_range: List[float] = [12.0, 15.0]  # [min, max] m/s
    safe_distance_range: List[float] = [2.0, 5.0]  # [min, max] meters
    acceleration_range: List[float] = [0.5, 1.0]  # [min, max] m/s²
    deceleration_range: List[float] = [1.0, 1.5]  # [min, max] m/s²
    queue_spacing_range: List[float] = [6.0, 10.0]  # [min, max] meters


class SimulationRequest(BaseModel):
    """Request to start a simulation."""

    border_config: BorderCrossingConfig
    simulation_config: Optional[SimulationConfig] = None
    phone_config: Optional[PhoneConfig] = None
    physics_config: Optional[PhysicsConfig] = None
    physics_ranges: Optional[PhysicsRanges] = None  # Ranges for random selection

    # Simplified interface - only need crossing name and direction
    crossing_name: str = "paso_del_norte"  # Name of border crossing
    direction: str = "mx2usa"  # Traffic direction: "mx2usa" or "usa2mx"

    # Visual queue spacing (meters between cars when displayed) - deprecated, use physics_ranges
    queue_spacing: float = 8.0

    # Legacy support (optional, ignored if crossing_name provided)
    geojson_path: Optional[str] = None
    use_dynamic_paths: bool = True  # Always use dynamic paths now
    country_of_origin: Optional[str] = None  # Deprecated, use direction instead


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


class ServiceNodeConfig(BaseModel):
    """Configuration for updating a service node."""
    service_rate: float = Field(..., gt=0, description="Service rate in cars/minute")
    service_time_variation: float = Field(0.2, ge=0, le=1, description="Coefficient of variation")


class AddServiceNodeRequest(BaseModel):
    """Request to add a new service node to a queue."""
    queue_id: int = Field(..., ge=0, description="Queue ID to add node to")
    service_rate: float = Field(3.0, gt=0, description="Service rate in cars/minute")
    service_time_variation: float = Field(0.2, ge=0, le=1, description="Coefficient of variation")


async def run_simulation(simulation_id: str):
    """
    Run the simulation in the background with real-time WebSocket updates.
    """
    sim = simulations.get(simulation_id)
    if not sim:
        return

    simulation = sim["simulation"]
    try:
        print(f"executing multi-queue border crossing simulation... ID: {simulation_id}")

        # Wait for WebSocket clients to connect (up to 2 seconds)
        import asyncio
        for i in range(20):
            if simulation_id in websockets and len(websockets[simulation_id]) > 0:
                break
            await asyncio.sleep(0.1)

        simulation.simulation_state["running"] = True
        iteration = 0

        while simulation.simulation_state["running"]:
            try:
                iteration += 1
                dt = simulation.advance_time()
                simulation.border_crossing.advance_time(dt)
                if not simulation.should_continue():
                    simulation.simulation_state["running"] = False
                simulation.record_positions()

                # Send real-time update
                # Collect car data with queue-position-based visual spacing
                cars_data = []

                # Get queue spacing from ranges or default
                if sim["request"].physics_ranges:
                    qs_range = sim["request"].physics_ranges.queue_spacing_range
                    queue_spacing = (qs_range[0] + qs_range[1]) / 2  # Use average for consistent spacing
                else:
                    queue_spacing = sim["request"].queue_spacing

                for queue in simulation.border_crossing.queues:
                    # Collect queued cars and sort by queue_start_time (arrival order)
                    queued_cars = [c for c in queue.cars.values() if c.status == "queued" and c.queue_start_time is not None]
                    queued_cars.sort(key=lambda c: c.queue_start_time)  # Earlier arrivals first

                    # Assign queue positions (1 = first to arrive = front of queue)
                    for idx, car in enumerate(queued_cars):
                        car.queue_position = idx + 1  # 1-indexed

                    # Process all cars in this queue
                    for car in queue.cars.values():
                        # Get car-specific waitline or use shared waitline
                        car_waitline = car.waitline if hasattr(car, 'waitline') and car.waitline else simulation.waitline

                        # Get GPS position along car's waitline
                        position_point = None
                        position_coords = [0, 0]

                        if car_waitline:
                            # For queued cars, use queue position for visual spacing
                            # Cars display at: path_end - (queue_position - 1) * spacing
                            # So first car (position 1) is at path_end, second is spacing meters back, etc.
                            if car.status == "queued" and car.queue_position is not None:
                                path_length = car_waitline.waitline_length
                                visual_pos = max(0, path_length - (car.queue_position - 1) * queue_spacing)
                                position_point = car_waitline.compute_position_at_distance_from_start(visual_pos)
                            else:
                                # Approaching/serving/completed - use actual physics position
                                position_point = car_waitline.compute_position_at_distance_from_start(car.position)
                            if position_point and simulation.bounds_polygon:
                                # Constrain position to bounds
                                position_point = constrain_point_to_bounds(
                                    position_point, simulation.bounds_polygon
                                )

                            # Convert UTM to lat/lon coordinates
                            if position_point:
                                position_coords = car_waitline.utm_to_latlon(
                                    position_point
                                )

                        # Get car's path GeoJSON if available
                        car_path_geojson = None
                        if car_waitline and hasattr(car_waitline, 'get_path_geojson'):
                            try:
                                car_path_geojson = car_waitline.get_path_geojson()
                            except Exception as e:
                                print(f"Error getting path for car {car.car_id}: {e}")

                        car_data = {
                            "id": str(car.car_id),
                            "position": position_coords,
                            "status": car.status,
                            "status_start_time": float(car.status_start_time) if car.status_start_time is not None else None,
                            "queue_position": int(car.queue_position) if car.queue_position is not None else None,
                            "velocity": float(car.velocity) if car.velocity is not None else None,
                            "acceleration": float(car.acceleration) if car.acceleration is not None else None,
                            "queue_id": int(car.queue_id) if car.queue_id is not None else None,
                            "arrival_time": float(car.arrival_time) if car.arrival_time is not None else None,
                            "queue_start_time": float(car.queue_start_time) if car.queue_start_time is not None else None,
                            "service_start_time": float(car.service_start_time) if car.service_start_time is not None else None,
                            "completion_time": float(car.completion_time) if car.completion_time is not None else None,
                            "wait_time": float(car.wait_time) if car.wait_time is not None else None,
                            "distance_traveled": float(car.position) if car.position is not None else None,
                            "path": car_path_geojson,  # Include car's unique path
                        }
                        cars_data.append(car_data)

                # Collect queue data
                queues_data = []
                for i, queue in enumerate(simulation.border_crossing.queues):
                    throughput = len([node for node in queue.service_nodes if node.is_busy])
                    queues_data.append(
                        {"length": len(queue.car_positions), "throughput": throughput}
                    )

                # Calculate average wait time from completed cars history
                completed_cars = simulation.border_crossing.completed_cars
                avg_wait_time = None

                if completed_cars:
                    # Calculate from cars that have both arrival and service start times
                    wait_times = [
                        car.service_start_time - car.arrival_time
                        for car in completed_cars
                        if car.service_start_time and car.arrival_time and car.service_start_time >= car.arrival_time
                    ]
                    if wait_times:
                        avg_wait_time = sum(wait_times) / len(wait_times)

                # Get traffic control points from waitline
                traffic_control_points = []
                if simulation.border_crossing.queues:
                    first_queue = simulation.border_crossing.queues[0]
                    if first_queue.waitline:
                        traffic_control_points = first_queue.waitline.traffic_control_points

                # Get service node states
                service_nodes_data = []
                for i, queue in enumerate(simulation.border_crossing.queues):
                    for node in queue.service_nodes:
                        node_state = node.get_state(i)
                        service_nodes_data.append({
                            "node_id": node_state.node_id,
                            "queue_id": node_state.queue_id,
                            "is_busy": node_state.is_busy,
                            "current_car_id": node_state.current_car_id,
                            "service_rate": node_state.service_rate,
                            "total_served": node_state.total_served,
                            "total_service_time": node_state.total_service_time,
                        })

                message = {
                    "type": "simulation_update",
                    "data": {
                        "cars": cars_data,
                        "queues": queues_data,
                        "metrics": {
                            "total_arrivals": int(simulation.border_crossing.total_arrivals),
                            "total_completions": int(simulation.border_crossing.total_completions),
                            "average_wait_time": float(avg_wait_time) if avg_wait_time is not None else None,
                            "simulation_time": float(simulation.temporal_state.get('simulation_time', 0)),
                        },
                        "traffic_control_points": traffic_control_points,
                        "service_nodes": service_nodes_data,
                    },
                }

                # Log simulation progress every 100 iterations (~10 seconds)
                if iteration % 100 == 0:
                    # Count cars by status
                    serving_count = sum(1 for q in simulation.border_crossing.queues for c in q.cars.values() if c.status == "serving")
                    queued_count = sum(1 for q in simulation.border_crossing.queues for c in q.cars.values() if c.status == "queued")
                    approaching_count = sum(1 for q in simulation.border_crossing.queues for c in q.cars.values() if c.status == "approaching")
                    completed_count = len(simulation.border_crossing.completed_cars)
                    avg_wait_str = f"{avg_wait_time:.1f}s" if avg_wait_time else "N/A"
                    print(f"Simulation {simulation_id}: {len(cars_data)} cars active (approaching={approaching_count}, queued={queued_count}, serving={serving_count}), arrivals={simulation.border_crossing.total_arrivals}, completed={completed_count}, avg_wait={avg_wait_str}, time={simulation.temporal_state['simulation_time']:.1f}s")

                if simulation_id in websockets:
                    for ws in websockets[simulation_id]:
                        try:
                            await ws.send_json(message)
                        except Exception as e:
                            print(f"Error sending WebSocket message: {e}")

                # Small delay to prevent flooding
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"ERROR in simulation loop iteration {iteration}: {e}")
                import traceback
                traceback.print_exc()
                # Continue running unless it's a critical error
                if "running" not in simulation.simulation_state:
                    break

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
            "total_arrivals": final_stats.execution_stats.total_arrivals,
            "total_completions": final_stats.execution_stats.total_completions,
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
        # Load and cache OSM graph (will be reused for all cars)
        from cascabel.paths.utils.optimized_path_generator import load_and_cache_graph
        graph = load_and_cache_graph(request.crossing_name)

        # Create a reference waitline (each car gets its own optimized path)
        from cascabel.models.optimized_waitline import OptimizedWaitLine
        waitline = OptimizedWaitLine(
            crossing_name=request.crossing_name,
            direction=request.direction,
            graph=graph,
            starting_point=None  # Random for reference
        )

        # Apply physics config to border config if provided
        border_cfg = request.border_config
        if request.physics_config:
            border_cfg.safe_distance = request.physics_config.safe_distance_meters

        # Create simulation with provided configs
        simulation = Simulation(
            waitline=waitline,
            border_config=border_cfg,
            simulation_config=request.simulation_config,
            phone_config=request.phone_config,
        )

        # Configure border crossing for optimized dynamic paths
        simulation.border_crossing.use_dynamic_paths = True
        simulation.border_crossing.crossing_name = request.crossing_name
        simulation.border_crossing.graph = graph
        simulation.border_crossing.direction = request.direction
        simulation.border_crossing.default_country = "mexico" if request.direction == "mx2usa" else "usa"

        # Store physics config for use during simulation
        if request.physics_config:
            simulation.physics_config = request.physics_config

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
        # Log full traceback for debugging
        error_traceback = traceback.format_exc()
        print(f"Error starting simulation: {error_traceback}")

        raise HTTPException(
            status_code=400,
            detail=f"Failed to start simulation: {str(e)}\n\nTraceback:\n{error_traceback}"
        )


@router.post("/simulation/{simulation_id}/stop", response_model=Dict[str, str])
async def stop_simulation(simulation_id: str):
    """
    Stop a running simulation and save telemetry data to database.

    Args:
        simulation_id: ID of the simulation to stop

    Returns:
        Status message with database save information
    """
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]

    # Mark simulation as stopped
    sim["status"] = "stopped"
    sim["end_time"] = datetime.now()

    # Stop the simulation loop
    simulation = sim["simulation"]
    simulation.simulation_state["running"] = False

    # Give the simulation loop a moment to finish its current iteration
    await asyncio.sleep(0.5)

    try:
        # Collect telemetry data from all cars
        db = TelemetryDatabase()

        # Collect all cars from all queues
        all_cars = []
        for queue in simulation.border_crossing.queues:
            all_cars.extend(queue.cars.values())
        # Also include completed cars
        all_cars.extend(simulation.border_crossing.completed_cars)

        # Save simulation metadata
        avg_wait_time = simulation.border_crossing.get_average_wait_time()
        db.save_simulation_metadata(
            simulation_id=simulation_id,
            start_time=sim["start_time"].timestamp(),
            end_time=sim["end_time"].timestamp(),
            total_cars=len(all_cars),
            total_arrivals=simulation.border_crossing.total_arrivals,
            total_completions=simulation.border_crossing.total_completions,
            average_wait_time=avg_wait_time if avg_wait_time and avg_wait_time > 0 else None,
            border_crossing=sim["request"].geojson_path.split("/")[-1].replace(".geojson", ""),
            geojson_path=sim["request"].geojson_path,
        )

        # Collect all telemetry records from all cars
        telemetry_records = []
        for car in all_cars:
            if hasattr(car, "telemetry_records") and car.telemetry_records:
                for record in car.telemetry_records:
                    # Calculate wait time if car has completed service
                    wait_time = None
                    if car.service_start_time and car.arrival_time:
                        wait_time = car.service_start_time - car.arrival_time

                    # Extract telemetry data - the record has field names like locationLatitude, not nested objects
                    telemetry_records.append(
                        {
                            "simulation_id": simulation_id,
                            "car_id": car.car_id,
                            "timestamp": record.get("locationTimestamp_since1970", 0),
                            "latitude": record.get("locationLatitude", 0.0),
                            "longitude": record.get("locationLongitude", 0.0),
                            "altitude": record.get("locationAltitude", 0.0),
                            "gps_accuracy": record.get("locationHorizontalAccuracy", 0.0),
                            "speed": record.get("locationSpeed", 0.0),
                            "heading": record.get("locationTrueHeading", 0.0),
                            "acceleration_x": record.get("accelerometerAccelerationX", 0.0),
                            "acceleration_y": record.get("accelerometerAccelerationY", 0.0),
                            "acceleration_z": record.get("accelerometerAccelerationZ", 0.0),
                            "car_status": car.status,
                            "queue_id": car.queue_id,
                            "position_on_path": car.position,
                            "arrival_time": car.arrival_time,
                            "service_start_time": car.service_start_time,
                            "completion_time": car.completion_time,
                            "wait_time": wait_time,
                        }
                    )

        # Save telemetry data in batch
        if telemetry_records:
            db.save_telemetry_batch(telemetry_records)

        db.close()

        # Close any open websockets
        if simulation_id in websockets:
            for ws in websockets[simulation_id]:
                try:
                    await ws.close()
                except Exception:
                    pass
            del websockets[simulation_id]

        return {
            "simulation_id": simulation_id,
            "status": "stopped",
            "message": f"Simulation stopped. Saved {len(telemetry_records)} telemetry records to database.",
            "telemetry_records_saved": len(telemetry_records),
            "database_path": db.db_path,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop simulation and save data: {str(e)}",
        )


@router.get("/simulation/{simulation_id}/car/{car_id}")
async def get_car_details(simulation_id: str, car_id: int):
    """
    Get detailed statistics for a specific car.

    Args:
        simulation_id: ID of the simulation
        car_id: ID of the car

    Returns:
        Comprehensive car statistics including timing, speed, distance, etc.
    """
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = simulations[simulation_id]
    simulation = sim["simulation"]

    # Check car_history in border_crossing
    if car_id in simulation.border_crossing.car_history:
        car = simulation.border_crossing.car_history[car_id]
        return car.get_comprehensive_stats()

    # If not in history, check active cars in all queues
    for queue in simulation.border_crossing.queues:
        if car_id in queue.cars:
            car = queue.cars[car_id]
            return car.get_comprehensive_stats()

    raise HTTPException(status_code=404, detail=f"Car {car_id} not found")


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
    simulation_id: str, node_id: str, config: ServiceNodeConfig
):
    """Update the configuration of a specific service node."""
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
                    node.service_rate = config.service_rate
                    node.service_time_variation = config.service_time_variation
                    node_found = True
                    break
            if node_found:
                break

        if not node_found:
            raise HTTPException(status_code=404, detail="Service node not found")

        return {
            "node_id": node_id,
            "service_rate": config.service_rate,
            "service_time_variation": config.service_time_variation,
            "message": "Service node configuration updated",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to update service node: {str(e)}"
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

        # Get traffic control points from waitline
        traffic_control_points = []
        if sim["simulation"].border_crossing.queues:
            first_queue = sim["simulation"].border_crossing.queues[0]
            if first_queue.waitline:
                traffic_control_points = first_queue.waitline.traffic_control_points

        return {
            "simulation_id": simulation_id,
            "status": sim["status"],
            "current_time": sim["current_time"],
            "cars": cars,
            "service_nodes": service_nodes,
            "statistics": stats.model_dump(),
            "traffic_control_points": traffic_control_points,
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
async def add_service_station(simulation_id: str, request: AddServiceNodeRequest):
    """Add a new service station to the specified queue."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_data = simulations[simulation_id]
    border_crossing = sim_data["simulation"].border_crossing

    # Validate queue ID
    if request.queue_id >= len(border_crossing.queues):
        raise HTTPException(status_code=400, detail="Invalid queue ID")

    queue = border_crossing.queues[request.queue_id]

    # Create new service node with custom configuration
    node_id = f"q{request.queue_id}_n{len(queue.service_nodes)}"
    new_node = ServiceNode(node_id, request.service_rate, request.service_time_variation)

    # Add to queue and border crossing
    queue.service_nodes.append(new_node)
    border_crossing.service_nodes.append(new_node)

    return {
        "station_id": node_id,
        "queue_id": request.queue_id,
        "service_rate": request.service_rate,
        "service_time_variation": request.service_time_variation,
    }


@router.delete("/simulation/{simulation_id}/service_node/{node_id}")
async def remove_service_node(simulation_id: str, node_id: str):
    """Remove a service node from the simulation."""
    if simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_data = simulations[simulation_id]
    border_crossing = sim_data["simulation"].border_crossing

    # Find and remove the service node
    node_found = False
    for queue in border_crossing.queues:
        for i, node in enumerate(queue.service_nodes):
            if node.node_id == node_id:
                # Don't allow removing if it's the only node in the queue
                if len(queue.service_nodes) <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot remove the last service node from a queue"
                    )

                # Remove from queue
                queue.service_nodes.pop(i)

                # Remove from border crossing
                border_crossing.service_nodes = [
                    n for n in border_crossing.service_nodes if n.node_id != node_id
                ]

                node_found = True
                break
        if node_found:
            break

    if not node_found:
        raise HTTPException(status_code=404, detail="Service node not found")

    return {
        "node_id": node_id,
        "message": "Service node removed successfully",
    }


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
    """Get list of available border crossing GeoJSON files with metadata."""
    crossings = []

    # Scan for geojson files in paths
    for root, dirs, files in os.walk("cascabel/paths"):
        for file in files:
            if file.endswith(".geojson") and not file.endswith("copy.geojson"):
                full_path = os.path.join(root, file)

                # Extract crossing info from path
                rel_path = os.path.relpath(root, "cascabel/paths")
                parts = rel_path.split(os.sep)

                # Read GeoJSON metadata
                try:
                    with open(full_path, 'r') as f:
                        geojson_data = json.load(f)

                    properties = geojson_data.get('features', [{}])[0].get('properties', {})
                    geom = geojson_data.get('features', [{}])[0].get('geometry', {})

                    direction = properties.get('direction', parts[0] if len(parts) >= 1 else 'unknown')
                    crossing_name = properties.get('crossing_name', file.replace(".geojson", ""))

                    # Construct relative path from cascabel/paths
                    geojson_rel_path = os.path.relpath(full_path, "cascabel/paths")

                    crossing = {
                        "id": file.replace(".geojson", ""),
                        "name": crossing_name,
                        "direction": direction,
                        "path": f"cascabel/paths/{geojson_rel_path}",
                        "description": properties.get('description', ''),
                        "start_point": properties.get('start_point'),
                        "end_point": properties.get('end_point'),
                        "geometry_type": geom.get('type', 'Unknown')
                    }

                    crossings.append(crossing)
                except Exception as e:
                    print(f"Error reading {full_path}: {e}")
                    continue

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


@router.get("/crossing/{crossing_name}/config")
async def get_crossing_config(crossing_name: str):
    """
    Get configuration data for a specific crossing including slowdown zones.

    Args:
        crossing_name: Name of the crossing (e.g., "paso_del_norte", "bridge_of_the_americas")

    Returns:
        Crossing configuration including preferred_queue_geometry and slowdown_zones
    """
    import json
    import os

    # Load bounding_boxes.json
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    bounding_boxes_path = os.path.join(root_dir, "cascabel", "paths", "bounding_boxes.json")

    if not os.path.exists(bounding_boxes_path):
        raise HTTPException(
            status_code=404, detail="Bounding boxes configuration not found"
        )

    try:
        with open(bounding_boxes_path, "r") as f:
            all_crossings = json.load(f)

        if crossing_name not in all_crossings:
            raise HTTPException(
                status_code=404,
                detail=f"Crossing '{crossing_name}' not found. Available: {list(all_crossings.keys())}"
            )

        return all_crossings[crossing_name]
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing bounding boxes: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading crossing config: {str(e)}")


@router.get("/geojson/{path_name:path}")
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
