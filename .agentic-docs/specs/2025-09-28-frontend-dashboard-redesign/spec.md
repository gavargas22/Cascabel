# Spec Requirements Document

> Spec: frontend-dashboard-redesign
> Created: 2025-09-28

## Overview

Redesign the entire frontend application using BlueprintJS to create a simple, fully functional dashboard for managing border traffic simulations. The dashboard will provide interfaces for creating new simulations, configuring parameters, running simulations, and viewing results.

## User Stories

### Simulation Creation and Configuration

As a researcher, I want to create a new simulation by specifying border crossing parameters and simulation settings, so that I can customize the simulation to match real-world scenarios.

**Detailed Workflow:** User navigates to the dashboard, selects "Create Simulation" tab, fills out forms for border config (num queues, service rates, etc.), simulation config (duration, telemetry), and phone config if needed, then saves the configuration for later use or proceeds to run.

### Simulation Execution and Monitoring

As a simulation enthusiast, I want to start a simulation run and monitor its progress in real-time, so that I can observe the queue dynamics and car movements as they happen.

**Detailed Workflow:** After configuring, user clicks "Run Simulation", sees progress bar, status updates, and real-time visualization of queues and cars. Can pause or cancel if needed.

### Results Analysis

As a scientist, I want to view and download simulation results including telemetry data and statistics, so that I can analyze the performance and export data for further study.

**Detailed Workflow:** Once simulation completes, user views summary stats (total arrivals, completions), downloads CSV telemetry, and sees basic charts of queue lengths over time.

## Spec Scope

1. **Dashboard Layout** - Main dashboard with tabs for Create, Configure, Run, Results
2. **Configuration Forms** - Forms for border config, simulation config, phone config using BlueprintJS form components
3. **Simulation Runner** - Interface to start simulations, show status, progress, and real-time updates via WebSocket
4. **Results Display** - Basic visualization of results with stats and download options

## Out of Scope

- Advanced data visualizations (e.g., complex charts beyond basic line/bar)
- Simulation editing or modification after creation
- Multi-simulation comparison
- User authentication or multi-user features
- Backend API modifications

## Expected Deliverable

1. A React dashboard built with BlueprintJS that allows users to create, parameterize, and run border traffic simulations
2. Real-time monitoring of simulation progress with queue and car visualizations
3. Downloadable telemetry data in CSV format
4. Clean, simple UI focused on functionality over aesthetics