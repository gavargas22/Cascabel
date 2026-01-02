# Cascabel

![alt text](https://github.com/gavargas22/Cascabel/raw/master/cascabel.jpg "Cascabel")

Simulates traffic on the border bridges with realistic car queue modeling and telemetry generation.

## Features

### Core Simulation
- **M/M/1 Queue Simulation**: Implements queuing theory for realistic car arrival and service patterns
- **Physics-Based Car Movement**: Enhanced car models with acceleration, velocity limits, and realistic physics
- **Multi-Queue System**: Support for multiple parallel queues with configurable service nodes
- **Realistic Telemetry Generation**: Generates GPS, accelerometer, and motion data matching real mobile device sensors
- **GeoJSON Boundary Support**: Define border crossing geometries with polygon constraints

### API & Real-time
- **REST API**: FastAPI-based server with 15+ endpoints for simulation management
- **WebSocket Streaming**: Live simulation state updates with car positions and queue metrics
- **Dynamic Control**: Adjust service rates, add stations, and modify simulation speed in real-time

### Visualization
- **Interactive Map View**: Real-time car tracking on Mapbox GL with service station visualization
- **Historical Playback**: Load and animate completed simulations from telemetry CSV files
- **Playback Controls**: Play/pause, seek, and adjustable speed for reviewing simulation history
- **Car Monitoring Dashboard**: Detailed metrics for individual vehicles with selection highlighting
- **Queue Visualization**: Live queue state display with length and throughput metrics

### Configuration
- **Phone Parameters**: Configurable sampling rates, sensor noise, and device orientations
- **Service Node Management**: Independent service rates per node with dynamic adjustment
- **Queue Assignment Strategies**: Shortest, round-robin, or random queue selection

## Future Enhancements

### Geographic Expansion
- **Multi-Border Support**: US-Mexico and US-Canada border crossings
- **Dynamic GeoJSON Loading**: Support for custom border crossing geometries
- **Crossing-Specific Simulation**: Unique traffic patterns per border location

### Advanced Lane Dynamics
- **Lane Switching**: Realistic simulation of cars changing lanes
- **Multi-Lane Queues**: Support for crossings with multiple parallel lanes
- **Enhanced Gyroscope Data**: Rotational motion simulation during lane changes

## Quick Start

### Installation

This project uses `uv` for Python package management. Install dependencies using:

```bash
uv pip install -r requirements.txt
```

Or add individual packages:
```bash
uv add package_name
```

### Running the API

```bash
uv run python scripts/run_api.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Running Scripts

All Python scripts should be run using `uv`:

```bash
uv run python your_script.py
```

### Testing

```bash
uv run python -m unittest
```

### Basic Usage

```python
# Start a simulation
curl -X POST "http://localhost:8000/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_config": {
      "arrival_rate": 0.5,
      "service_rate": 0.8
    },
    "phone_config": {
      "sampling_rate": 10
    },
    "simulation_config": {
      "duration": 3600
    }
  }'
```

## API Endpoints

### Simulation Control
- `POST /simulate` - Start a new simulation
- `POST /grand-simulate` - Start simulation with grand configuration
- `GET /simulations` - List all active simulations
- `GET /simulation/{id}/status` - Get simulation status
- `GET /simulation/{id}/state` - Get detailed simulation state
- `DELETE /simulation/{id}` - Stop and remove simulation

### Real-time Updates
- `WebSocket /ws/{id}` - Real-time simulation state streaming
- `GET /simulation/{id}/telemetry` - Download telemetry data (CSV/JSON)

### Dynamic Control
- `PUT /simulation/{id}/time_speed` - Adjust simulation speed (time factor)
- `PUT /simulation/{id}/service_node/{node_id}` - Update service node rate
- `POST /simulation/{id}/add_car` - Add cars to running simulation
- `POST /simulation/{id}/add_station` - Add service stations dynamically

### GeoJSON Management
- `GET /geojson/{path_name}` - Load GeoJSON boundary files
- `GET /border-crossings` - List available border crossings
- `POST /border-crossings/{id}/load` - Load specific border crossing configuration

## Project Structure

```
cascabel/
├── api/                    # FastAPI backend server
│   ├── main.py            # Application entry point
│   └── routers/           # API route handlers
│       └── simulations.py # Simulation endpoints
├── cascabel/              # Core simulation engine
│   ├── models/            # Domain models
│   │   ├── car.py         # Physics-based car model
│   │   ├── waitline.py    # GeoJSON path representation
│   │   ├── queue.py       # Queue management
│   │   ├── border_crossing.py  # Multi-queue coordinator
│   │   ├── simulation.py  # Main orchestrator
│   │   └── queuing/       # M/M/1 implementation
│   ├── simulation/
│   │   └── telemetry/     # Sensor data generators
│   ├── utils/             # Utilities
│   │   ├── geojson_loader.py      # GeoJSON parsing
│   │   └── bounding_validator.py # Boundary constraints
│   └── tests/             # Backend unit tests
├── frontend/              # React TypeScript application
│   └── src/
│       ├── components/    # UI components
│       │   ├── RealtimeMapView.tsx      # Live map visualization
│       │   ├── MapviewPanel.tsx         # Interactive map panel
│       │   ├── CarTelemetryDashboard.tsx # Individual car metrics
│       │   ├── ConfigurePanel.tsx       # Simulation setup
│       │   ├── RunPanel.tsx             # Control panel
│       │   ├── QueueVisualization.tsx   # Queue display
│       │   └── ResultsPanel.tsx         # Results download
│       └── services/
│           └── api.ts     # Type-safe API client
├── .claude/               # Claude Code agent configurations
│   ├── agents/            # Custom AI agents
│   ├── skills/            # Reusable AI skills
│   ├── CLAUDE.md          # Project context
│   └── settings.json      # Agent configuration
├── .agentic-docs/         # Agent OS documentation
│   ├── product/           # Product mission & roadmap
│   ├── specs/             # Feature specifications
│   └── recaps/            # Implementation summaries
├── raw_data/              # Real telemetry samples
└── tests/                 # Backend unit tests
```

## Docker Setup

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for containers

### Quick Start with Docker:

```bash
# Start both services
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Docker Commands:

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild
docker-compose up --build
```

### Development with Docker

For development with hot reload:

```bash
# Start only backend
docker-compose up backend

# Start only frontend
docker-compose up frontend

# Run tests in container
docker-compose exec backend uv run python -m unittest
```

## VSCode Debugging

### Prerequisites

- VSCode with Python and JavaScript/TypeScript extensions
- Python Debugger extension (`ms-python.debugpy`)
- Chrome Debugger extension (optional)

### Debug Configurations

The project includes basic debug configurations in `.vscode/launch.json`:

1. **Debug API** - Debug the Python FastAPI server
2. **Debug Frontend** - Debug the React development server
3. **Debug Frontend in Chrome** - Debug in Chrome browser

### Using Debug Configurations

1. Open the project in VSCode
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select a configuration from the dropdown
4. Click the green play button or press F5

### Debug Tasks

Additional tasks are available in `.vscode/tasks.json`:

- `docker-compose:up` - Start Docker services
- `docker-compose:down` - Stop Docker services
- `install-frontend-deps` - Install npm dependencies
- `install-backend-deps` - Install Python dependencies
- `start-backend` - Start backend server
- `start-frontend` - Start frontend server

## Testing

Test contained in `cascabel/tests/` can be run using the standard python library `unittest` by running the following command.

```bash
python -m unittest
```

## Development

### Agent OS Integration

This project uses [Agent OS](https://github.com/buildermethods/agent-os) for AI-assisted development with Claude Code. The `.claude/` directory contains:

- **Agents**: Specialized AI assistants for planning, spec creation, and task execution
- **Skills**: Reusable workflows for common development tasks
- **CLAUDE.md**: Project context and development guidelines
- **settings.json**: Agent configuration and tool permissions

To use the agents:
```bash
# Create a new feature spec
Use the create-spec agent to plan my next feature

# Execute tasks from a spec
Use the execute-tasks agent to implement the current spec
```

### Documentation

Comprehensive documentation in `.agentic-docs/` includes:
- **Product**: Mission statement, tech stack, and roadmap
- **Specs**: Detailed feature specifications with technical details
- **Recaps**: Post-implementation summaries of completed features

### Recent Additions

- **Mapview Realtime Visualization** (2025-09-28): Live car tracking, historical playback, and individual car dashboards
- **Near-Realtime Queue Visualization** (2025-09-28): Mapbox integration, WebSocket streaming, and dynamic station management
- **GeoJSON Boundaries**: Support for multiple border crossings with polygon constraints
- **Claude Code Migration**: Modernized agent structure following latest standards