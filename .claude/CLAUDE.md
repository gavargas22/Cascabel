# Cascabel Project Context

## Product Overview

Cascabel is a border crossing simulation tool that helps researchers, scientists, and simulation enthusiasts model realistic car queues and telemetry data by providing physics-based movement simulations and sensor data generation from smartphone-like devices.

Cascabel serves researchers and scientists who need accurate traffic simulations for analysis and modeling. Unlike basic queue tools, Cascabel incorporates realistic physics, telemetry, and human behaviors like lane switching for more adaptable and precise simulations.

## Technical Stack

### Backend
- **Framework**: FastAPI 0.104.1 (Python)
- **Database**: In-memory (potential for PostgreSQL addition)
- **Deployment**: Docker Compose

### Frontend
- **Framework**: React 19.1.1
- **Import Strategy**: node
- **CSS Framework**: BlueprintJS 6.3.1
- **UI Components**: BlueprintJS
- **Icons**: BlueprintJS Icons 6.1.0
- **Fonts**: Default browser fonts

### Infrastructure
- **Hosting**: Local/Docker
- **Asset Hosting**: Local
- **Repository**: https://github.com/gavargas22/Cascabel

## Agent OS Standards

### Development Workflow

When working with this project, follow the Agent OS workflow:

1. **Planning**: Use the `plan-product` agent for new product planning
2. **Specification**: Use the `create-spec` agent for feature specifications
3. **Task Breakdown**: Use the `create-tasks` agent to break specs into tasks
4. **Execution**: Use the `execute-tasks` agent to implement features
5. **Analysis**: Use the `analyze-product` agent to audit codebase

### Documentation Structure

All Agent OS documentation is stored in `.agentic-docs/`:
- `/product/` - Product vision, mission, tech stack, and roadmap
- `/specs/` - Feature specifications organized by date
- `/recaps/` - Post-implementation summaries

### Spec Format

Each spec follows this structure:
```
.agentic-docs/specs/YYYY-MM-DD-feature-name/
├── spec.md              # Full requirements
├── spec-lite.md         # Condensed for AI context
├── tasks.md             # Task breakdown
└── sub-specs/
    ├── technical-spec.md
    ├── api-spec.md (optional)
    └── database-schema.md (optional)
```

### Git Workflow

- Create branches based on spec folder names (without date prefix)
- Example: `2025-09-28-mapview-realtime-visualization` → `mapview-realtime-visualization` branch
- Always run tests before committing
- Follow conventional commit messages

## Key Features

### Current Implementation

- Real-time map visualization with telemetry playback
- GeoJSON boundary definitions for border crossings
- Physics-based vehicle movement simulation
- Queue management system
- Sensor telemetry generation

### Simulation Capabilities

- Realistic vehicle physics
- Lane switching behaviors
- Queue formation and progression
- Telemetry data from smartphone-like sensors
- Border crossing zone modeling

## Development Guidelines

### Code Style

- Follow existing patterns in the codebase
- Use TypeScript/Python type hints
- Keep components modular and reusable
- Write tests for new functionality (TDD approach)

### Testing

- Write tests before implementation (TDD)
- Ensure all tests pass before task completion
- Run full test suite before creating PRs

### File Organization

- Frontend: React components in organized directories
- Backend: FastAPI routes and services following separation of concerns
- Shared types and interfaces clearly defined

## Agent Behavior Notes

- Always check `.agentic-docs/product/mission-lite.md` for product alignment
- Reference `.agentic-docs/product/tech-stack.md` for technical decisions
- Follow the roadmap in `.agentic-docs/product/roadmap.md` for prioritization
- Use Test-Driven Development (TDD) approach
- Verify all tests pass before marking tasks complete

## Common Commands

- Run tests: `npm test` / `pytest`
- Start development: `docker-compose up`
- Build: `npm run build`
- Lint: `npm run lint`
