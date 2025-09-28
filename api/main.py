"""
Cascabel Simulation API
======================

FastAPI server for multi-queue border crossing simulation
with telemetry generation.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from .shared import simulations
from .routers.simulations import router as simulations_router

app = FastAPI(
    title="Cascabel Border Crossing Simulation API",
    description="API for simulating car queues at border crossings "
    "with realistic telemetry generation",
    version="1.0.0",
)

# Include routers
app.include_router(simulations_router, tags=["simulations"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    """WebSocket endpoint for real-time simulation updates."""
    await websocket.accept()

    try:
        while True:
            if simulation_id in simulations:
                sim = simulations[simulation_id]
                simulation_obj = sim["simulation"]
                
                # Get all cars with their positions
                cars_data = []
                for queue in simulation_obj.border_crossing.queues:
                    for car in queue.cars.values():
                        cars_data.append({
                            "car_id": car.car_id,
                            "position": car.position,
                            "velocity": car.velocity,
                            "status": car.status,
                            "queue_id": car.queue_id
                        })
                
                # Get service nodes status
                service_nodes_data = []
                for node in simulation_obj.border_crossing.service_nodes:
                    service_nodes_data.append({
                        "node_id": node.node_id,
                        "is_busy": node.is_busy,
                        "current_car_id": (
                            node.current_car.car_id
                            if node.current_car else None
                        ),
                        "queue_id": node.queue_id
                    })
                
                # Send comprehensive update
                data = {
                    "type": "simulation_update",
                    "simulation_id": simulation_id,
                    "status": sim["status"],
                    "current_time": sim["current_time"],
                    "time_factor": (
                        simulation_obj.simulation_config.time_factor
                    ),
                    "cars": cars_data,
                    "service_nodes": service_nodes_data,
                    "total_cars": len(cars_data),
                    "active_nodes": sum(
                        1 for node in service_nodes_data if node["is_busy"]
                    )
                }
                await websocket.send_json(data)

            # Wait before next update (1 second for near-realtime)
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        pass


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Cascabel Border Crossing Simulation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
