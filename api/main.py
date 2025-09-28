"""
Cascabel Simulation API
======================

FastAPI server for multi-queue border crossing simulation
with telemetry generation.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
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
                # Send current state (batched for efficiency)
                data = {
                    "type": "update",
                    "simulation_id": simulation_id,
                    "status": sim["status"],
                    "current_time": sim["current_time"],
                    "cars_count": len(sim["simulation"].border_crossing.get_all_cars()),
                    "service_nodes": len(
                        sim["simulation"].border_crossing.service_nodes
                    ),
                }
                await websocket.send_json(data)

            # Wait before next update (reduced frequency for efficiency)
            await asyncio.sleep(2.0)  # 2 second updates for performance

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
