# Technical Specification

This is the technical specification for the spec detailed in @.agentic-docs/specs/2025-09-26-grand-simulation-refactor/spec.md

## Technical Requirements

- Refactor API endpoints to be more modular, using FastAPI best practices for dependency injection and async operations.
- Enhance queuing models to M/M/c with time-varying rates, incorporating RSS feed data parsing for historical wait times.
- Implement simulation logic for 24-hour runs, with time steps optimized for performance (e.g., 1-minute increments).
- Develop efficient data streaming via WebSockets for real-time updates, with batching to reduce overhead.
- In React, use Leaflet for maps with marker clustering and virtualization to handle 1000+ cars without high CPU usage.
- Integrate historical data fetching from https://bwt.cbp.gov/api/bwtRss/rssbyportnum/HTML/POV/240201 using XML parsing libraries like xml.etree.ElementTree.

## External Dependencies

- **feedparser** - For parsing RSS feeds from CBP.
- **Justification:** Enables easy extraction of historical wait time data to inform simulation rates.
- **react-virtualized** - For efficient rendering of large lists in visualization.
- **Justification:** Improves performance when displaying many car markers or telemetry data points.