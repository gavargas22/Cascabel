# Spec Requirements Document

> Spec: Database Integration for Simulation History
> Created: 2026-01-01

## Overview

Add PostgreSQL database integration to Cascabel for persistent storage of simulation history, telemetry data, and configuration. This enables large-scale analysis, historical queries, and multi-user simulation management that currently isn't possible with in-memory storage.

## User Stories

### Historical Analysis Researcher

As a traffic researcher, I want to store and query past simulations, so that I can analyze trends across multiple border crossing scenarios and time periods without re-running simulations.

The researcher can access a historical database of simulations, filter by date/configuration, compare results across different parameters, and export aggregated statistics for research papers.

### Long-Running Simulation Manager

As a simulation administrator, I want simulations to persist across server restarts, so that long-running experiments aren't lost and can be resumed or analyzed later.

The administrator starts a simulation, monitors it through the web UI, stops the server for maintenance, and when restarting can see all previous simulations with their complete telemetry data available for download.

### Multi-User Collaboration

As a research team member, I want to share simulation results with colleagues, so that we can collaborate on analyzing border crossing patterns without manually transferring CSV files.

Team members can access a shared database, view each other's simulation configurations and results, filter by creator or date, and build on previous work.

## Spec Scope

1. **PostgreSQL Integration** - Add database connection, migrations, and ORM models for simulations, telemetry, and configurations
2. **Simulation Persistence** - Store simulation metadata, configuration, and results automatically when simulations complete
3. **Telemetry Storage** - Persist individual telemetry records with efficient querying and aggregation capabilities
4. **Historical Query API** - Endpoints for filtering, searching, and retrieving past simulations
5. **Migration System** - Database schema versioning with Alembic for future schema changes

## Out of Scope

- Real-time database writes during simulation (still use in-memory for performance)
- User authentication and authorization (single-user or trusted environment assumed)
- Database sharding or horizontal scaling
- Advanced analytics or BI tool integration (future enhancement)
- Automated backup and disaster recovery

## Expected Deliverable

1. PostgreSQL database running via Docker Compose with all simulation data persisted
2. API endpoints for querying historical simulations by date, configuration, or metadata
3. Automatic simulation result storage when simulations complete
4. Database migrations system with initial schema and version control
5. Updated documentation showing how to query historical data
