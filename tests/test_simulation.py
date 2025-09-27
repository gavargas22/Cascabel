import unittest
from unittest.mock import MagicMock, patch
from cascabel.models.simulation import Simulation
from cascabel.models.models import SimulationConfig, BorderCrossingConfig
from cascabel.models.waitline import WaitLine


class TestSimulation(unittest.TestCase):
    """Test cases for Simulation class duration and time stepping."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock waitline
        self.mock_waitline = MagicMock(spec=WaitLine)
        self.mock_waitline.destiny = {"line_length": 1000}
        self.mock_waitline.compute_position_at_distance_from_start.return_value = None

        # Create border config
        self.border_config = BorderCrossingConfig(
            num_queues=1,
            nodes_per_queue=[1],
            arrival_rate=1.0,
            service_rates=[2.0],
            safe_distance=10.0,
            max_queue_length=50,
        )

    def test_simulation_duration_max_time_reached(self):
        """Test simulation runs for max_simulation_time when no activity."""
        sim_config = SimulationConfig(
            max_simulation_time=10.0,
            time_factor=1.0,
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        with patch("cascabel.models.simulation.BorderCrossing") as mock_cls:
            mock_bc = MagicMock()
            mock_bc.queues = []
            mock_bc.get_statistics.return_value = (
                {
                    "total_arrivals": 0,
                    "total_completions": 0,
                    "current_time": 10.0,
                    "num_queues": 1,
                    "total_service_nodes": 1,
                    "queue_assignment_strategy": "shortest",
                    "overall_utilization": 0.0,
                    "throughput": 0.0,
                },
                [],
                [],
            )
            mock_cls.return_value = mock_bc

            simulation = Simulation(self.mock_waitline, self.border_config, sim_config)
            simulation()

            self.assertEqual(simulation.temporal_state["simulation_time"], 10.0)
            self.assertFalse(simulation.simulation_state["running"])

    def test_time_stepping_with_time_factor(self):
        """Test time stepping with different time factors."""
        sim_config = SimulationConfig(
            max_simulation_time=5.0,
            time_factor=2.0,
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        with patch("cascabel.models.simulation.BorderCrossing") as mock_cls:
            mock_bc = MagicMock()
            mock_bc.queues = []
            mock_bc.get_statistics.return_value = (
                {
                    "total_arrivals": 0,
                    "total_completions": 0,
                    "current_time": 5.0,
                    "num_queues": 1,
                    "total_service_nodes": 1,
                    "queue_assignment_strategy": "shortest",
                    "overall_utilization": 0.0,
                    "throughput": 0.0,
                },
                [],
                [],
            )
            mock_cls.return_value = mock_bc

            simulation = Simulation(self.mock_waitline, self.border_config, sim_config)
            simulation()

            self.assertGreaterEqual(simulation.temporal_state["simulation_time"], 5.0)
            self.assertLessEqual(simulation.temporal_state["simulation_time"], 6.0)

    def test_simulation_stops_at_max_time_with_activity(self):
        """Test simulation stops at max time with activity."""
        sim_config = SimulationConfig(
            max_simulation_time=8.0,
            time_factor=1.0,
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        with patch("cascabel.models.simulation.BorderCrossing") as mock_cls:
            mock_bc = MagicMock()
            mock_queue = MagicMock()
            mock_queue.cars = {"car1": MagicMock()}
            mock_bc.queues = [mock_queue]
            mock_bc.get_statistics.return_value = (
                {
                    "total_arrivals": 0,
                    "total_completions": 0,
                    "current_time": 8.0,
                    "num_queues": 1,
                    "total_service_nodes": 1,
                    "queue_assignment_strategy": "shortest",
                    "overall_utilization": 0.0,
                    "throughput": 0.0,
                },
                [],
                [],
            )
            mock_cls.return_value = mock_bc

            simulation = Simulation(self.mock_waitline, self.border_config, sim_config)
            simulation()

            self.assertEqual(simulation.temporal_state["simulation_time"], 8.0)
            self.assertFalse(simulation.simulation_state["running"])

    def test_advance_time_method(self):
        """Test advance_time method."""
        sim_config = SimulationConfig(
            max_simulation_time=100.0,
            time_factor=1.5,
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        simulation = Simulation(self.mock_waitline, self.border_config, sim_config)

        self.assertEqual(simulation.temporal_state["simulation_time"], 0)

        dt = simulation.advance_time()
        self.assertEqual(dt, 1.5)
        self.assertEqual(simulation.temporal_state["simulation_time"], 1.5)

        dt = simulation.advance_time()
        self.assertEqual(dt, 1.5)
        self.assertEqual(simulation.temporal_state["simulation_time"], 3.0)

    def test_should_continue_logic(self):
        """Test should_continue logic."""
        sim_config = SimulationConfig(
            max_simulation_time=10.0,
            time_factor=1.0,
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        simulation = Simulation(self.mock_waitline, self.border_config, sim_config)

        mock_bc = MagicMock()
        mock_queue = MagicMock()
        simulation.border_crossing = mock_bc

        # Under max time, no cars, under 300s -> continue
        simulation.temporal_state["simulation_time"] = 5.0
        mock_queue.cars = {}
        mock_bc.queues = [mock_queue]
        self.assertTrue(simulation.should_continue())

        # Over max time -> stop
        simulation.temporal_state["simulation_time"] = 15.0
        self.assertFalse(simulation.should_continue())

        # At max time -> stop
        simulation.temporal_state["simulation_time"] = 10.0
        self.assertFalse(simulation.should_continue())

        # Under max time, has cars -> continue
        simulation.temporal_state["simulation_time"] = 5.0
        mock_queue.cars = {"car1": MagicMock()}
        self.assertTrue(simulation.should_continue())


if __name__ == "__main__":
    unittest.main()
