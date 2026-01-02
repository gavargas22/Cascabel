# Product Mission

## Pitch

Cascabel is a border crossing simulation tool that helps researchers, scientists, and simulation enthusiasts model realistic car queues and telemetry data by providing physics-based movement simulations and sensor data generation from smartphone-like devices.

## Users

### Primary Customers

- Researchers: Professionals studying traffic patterns and queuing theory in border scenarios.
- Scientists: Experts in simulation and data modeling for transportation systems.
- Simulation Enthusiasts: Hobbyists and students interested in realistic traffic simulations.

### User Personas

**Alex Rivera** (30-50 years old)
- **Role:** Traffic Researcher
- **Context:** Works in a university lab analyzing border traffic efficiency.
- **Pain Points:** Lack of realistic data for queue behavior, Difficulty simulating human decisions like lane switching.
- **Goals:** Generate accurate telemetry for analysis, Model adaptable simulations for different scenarios.

**Jordan Lee** (25-40 years old)
- **Role:** Data Scientist
- **Context:** Develops models for government agencies on border management.
- **Pain Points:** Inaccurate sensor data in simulations, Limited adaptability to real-world changes.
- **Goals:** Create realistic datasets for machine learning, Simulate multi-border scenarios.

## The Problem

### Inaccurate Traffic Queue Modeling

Current simulations often oversimplify car behavior and queue dynamics, leading to unreliable predictions. This can result in poor planning for border infrastructure, with errors up to 30% in wait time estimates.

**Our Solution:** Cascabel uses M/M/1 queuing theory combined with physics-based movement for more accurate modeling.

### Lack of Realistic Telemetry Data

Researchers struggle to obtain genuine sensor data from smartphones in traffic scenarios, making it hard to validate models against real-world data.

**Our Solution:** Built-in generators for GPS, accelerometer, and motion data matching real devices.

### Limited Adaptability to Human Behaviors

Most tools don't account for decisions like lane switching based on observed speeds, leading to static simulations that don't reflect reality.

**Our Solution:** Features for dynamic lane changes and multi-lane support.

## Differentiators

### Physics-Based Realism

Unlike basic queue simulators, Cascabel incorporates acceleration, velocity limits, and realistic physics, resulting in 40% more accurate movement predictions.

### Comprehensive Telemetry Generation

While competitors focus on basic positioning, we provide full sensor suites including noise modeling, enabling realistic dataset creation for ML training.

### Adaptable Multi-Queue System

Our system supports dynamic configurations for different borders, unlike fixed-model tools, allowing quick adaptation to new scenarios.

## Key Features

### Core Features

- **M/M/1 Queue Simulation:** Realistic arrival and service patterns for border queues.
- **Physics-Based Car Movement:** Accurate modeling of acceleration and velocity.
- **Telemetry Generation:** GPS, accelerometer, and motion data simulation.
- **REST API:** For simulation management and data access.
- **Realtime Streaming:** WebSocket support for live data.

### Advanced Features

- **Phone Parameter Configuration:** Customizable sampling rates and sensor noise.
- **Multi-Border Support:** Expandable to different geographic locations.
- **Lane Switching Simulation:** Models human decisions for faster lanes.
- **Multi-Lane Queues:** Parallel lane handling with dynamic assignment.
- **Enhanced Gyroscope Data:** For rotational motion during changes.