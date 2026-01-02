# Technical Specification

This is the technical specification for the spec detailed in @.agentic-docs/specs/2026-01-01-database-integration/spec.md

## Technical Requirements

### Database Layer

- **ORM**: SQLAlchemy 2.0+ with async support for FastAPI integration
- **Migrations**: Alembic for database schema versioning and migrations
- **Connection Pooling**: Async connection pool with configurable size (default: 5-20 connections)
- **Database**: PostgreSQL 15+ via Docker container

### Schema Design

**Tables:**

1. **simulations**
   - id (UUID, primary key)
   - created_at (timestamp)
   - completed_at (timestamp, nullable)
   - status (enum: running, completed, failed)
   - configuration (JSONB) - stores BorderCrossingConfig, SimulationConfig
   - results (JSONB) - stores final BorderCrossingStats
   - duration_seconds (float)
   - car_count (integer)
   - queue_count (integer)

2. **telemetry_records**
   - id (bigint, auto-increment)
   - simulation_id (UUID, foreign key to simulations)
   - car_id (string)
   - timestamp_ms (bigint)
   - latitude (float)
   - longitude (float)
   - gps_data (JSONB) - full GPS record
   - accelerometer_data (JSONB)
   - motion_data (JSONB)
   - created_at (timestamp)
   - Index on: (simulation_id, car_id, timestamp_ms)

3. **queue_stats**
   - id (integer, auto-increment)
   - simulation_id (UUID, foreign key)
   - queue_id (integer)
   - total_arrivals (integer)
   - total_completions (integer)
   - avg_wait_time (float)
   - max_queue_length (integer)
   - utilization (float)

### API Endpoints

**New Endpoints:**

- `GET /simulations/history` - List historical simulations
  - Query params: start_date, end_date, status, limit, offset
  - Returns: paginated list of simulation metadata

- `GET /simulations/{id}/full` - Get simulation with telemetry
  - Returns: complete simulation with all telemetry records
  - Option to download as CSV

- `GET /simulations/stats` - Aggregated statistics
  - Query params: date_range, group_by (date, queue_count, etc.)
  - Returns: aggregated metrics across multiple simulations

- `DELETE /simulations/history/{id}` - Delete historical simulation

### Performance Considerations

- Batch insert telemetry records (1000+ at a time) when simulation completes
- Index on commonly queried fields (simulation_id, created_at, status)
- JSONB columns for flexible schema with GIN indexes for fast lookups
- Async database operations to avoid blocking FastAPI event loop
- Optional telemetry sampling for very large simulations (store every Nth record)

### Data Persistence Flow

1. Simulation starts → Create simulation record with status='running'
2. Simulation runs → Data stays in memory for performance
3. Simulation completes → Batch write:
   - Update simulation record (status='completed', results, completed_at)
   - Insert all telemetry records in batches
   - Insert queue statistics
4. API responds → Simulation ID for historical retrieval

### Configuration

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `DB_POOL_SIZE` - Connection pool size (default: 10)
- `DB_MAX_OVERFLOW` - Max overflow connections (default: 20)
- `ENABLE_TELEMETRY_PERSISTENCE` - Toggle telemetry storage (default: true)
- `TELEMETRY_SAMPLE_RATE` - Store 1 in N records (default: 1 = all)

## External Dependencies

- **sqlalchemy** (2.0+) - ORM and database toolkit
  - **Justification**: Industry-standard ORM with excellent async support and type safety

- **alembic** (1.13+) - Database migration tool
  - **Justification**: Standard migration tool for SQLAlchemy, version control for schema

- **asyncpg** (0.29+) - Async PostgreSQL driver
  - **Justification**: Fastest async Postgres driver for Python, required for async SQLAlchemy

- **psycopg2-binary** (2.9+) - PostgreSQL adapter (fallback)
  - **Justification**: Compatibility for synchronous operations if needed

### Docker Compose Update

Add PostgreSQL service:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cascabel
      POSTGRES_USER: cascabel
      POSTGRES_PASSWORD: cascabel_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cascabel"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```
