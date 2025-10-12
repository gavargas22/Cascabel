"""
Cascabel Simulation API
======================

FastAPI server for multi-queue border crossing simulation
with telemetry generation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from .routers import simulations

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

try:
    app = FastAPI(
        title="Cascabel Border Crossing Simulation API",
        description="API for simulating car queues at border crossings "
        "with realistic telemetry generation",
        version="1.0.0",
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(simulations.router)

    print("App created successfully")

except Exception as e:
    print(f"Error creating app: {e}")
    import traceback

    traceback.print_exc()
    exit(1)


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

    try:
        port = int(os.getenv("API_PORT", "8000"))
        print(f"Starting server on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback

        traceback.print_exc()
