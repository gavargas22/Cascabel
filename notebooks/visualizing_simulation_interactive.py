import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    from cascabel.models.waitline import WaitLine
    from cascabel.models.simulation import Simulation
    from cascabel.models.models import BorderCrossingConfig, SimulationConfig
    return BorderCrossingConfig, Simulation, SimulationConfig, WaitLine


@app.cell
def _(WaitLine):
    waitline = WaitLine(
        geojson_path="./cascabel/paths/usa2mx/bota.geojson",
        speed_regime={"slow": 0.8, "fast": 0.2},
        line_length_seed=0.5
    )
    return (waitline,)


@app.cell
def _(BorderCrossingConfig):
    border_config = BorderCrossingConfig(
        num_queues=3,
        nodes_per_queue=[2, 2, 2],
        arrival_rate=2.0,
        service_rates=[0.8, 0.9, 0.7, 0.85, 0.75, 0.9],
        queue_assignment='shortest',
        safe_distance=8.0,
        max_queue_length=50
    )
    return (border_config,)


@app.cell
def _(Simulation, SimulationConfig, border_config, waitline):
    simulation_config = SimulationConfig(
        max_simulation_time=3600.0,
        time_factor=1.0,
        enable_telemetry=True,
        enable_position_tracking=True
    )

    simulation = Simulation(
        waitline=waitline,
        border_config=border_config,
        simulation_config=simulation_config
    )

    return (simulation,)


@app.cell
def _(simulation):
    simulation()
    stats = simulation.get_statistics()
    return (stats,)


@app.cell
def _(stats):
    stats.queue_stats[0].average_wait_time
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
