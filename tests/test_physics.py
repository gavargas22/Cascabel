import unittest
from unittest.mock import MagicMock, patch
from cascabel.models.queue import CarQueue
from cascabel.models.waitline import WaitLine


class TestCarPhysics(unittest.TestCase):
    """Test cases for enhanced car physics with safe distances."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock waitline
        self.mock_waitline = MagicMock(spec=WaitLine)
        self.mock_waitline.destiny = {"line_length": 1000}

        # Create cars with 2m safe distance
        self.safe_distance = 2.0
        self.queue = CarQueue(
            self.mock_waitline,
            arrival_rate=0,  # Disable arrivals for physics tests
            safe_distance=self.safe_distance,
        )

    def test_safe_distance_constraint(self):
        """Test that cars maintain minimum 2m safe distance."""
        # Add two cars
        car1 = self.queue.add_car()
        car2 = self.queue.add_car()

        # Position cars: car1 ahead (higher position), car2 behind
        car1.position = 10.0
        car2.position = 7.0  # Close to car1, should trigger slowing

        # Set car1 as serving so it moves
        car1.set_status("serving")
        self.queue.serving_car = car1

        # Advance time - car1 should move, car2 should maintain distance
        self.queue.update_positions(1.0)

        # Car1 should be moving
        self.assertGreater(car1.velocity, 0, "Serving car should be moving")

        # Car2 should be slower to maintain safe distance
        self.assertLess(
            car2.velocity,
            car1.velocity,
            "Following car should be slower to maintain distance",
        )

    def test_acceleration_on_queue_progress(self):
        """Test that cars accelerate when the queue ahead moves."""
        # Add cars in queue
        car1 = self.queue.add_car()
        car2 = self.queue.add_car()
        car3 = self.queue.add_car()

        # Position cars with safe distances
        car1.position = 20.0
        car2.position = 15.0  # 5m behind car1
        car3.position = 10.0  # 5m behind car2

        # Set car1 as serving (moving at service speed)
        car1.set_status("serving")
        self.queue.serving_car = car1

        # Advance time
        self.queue.update_positions(1.0)

        # Car2 should accelerate towards car1's speed
        self.assertGreater(car2.velocity, 0, "Car behind serving car should accelerate")

        # Car3 should accelerate towards car2's speed
        self.assertGreater(
            car3.velocity, 0, "Car behind accelerating car should accelerate"
        )

    def test_inter_car_influence(self):
        """Test that movement of one car influences following cars."""
        # Add three cars
        car1 = self.queue.add_car()
        car2 = self.queue.add_car()
        car3 = self.queue.add_car()

        # Position with safe distances
        car1.position = 20.0
        car2.position = 15.0
        car3.position = 10.0

        # Car1 starts moving
        car1.set_status("serving")
        self.queue.serving_car = car1

        # Advance time
        self.queue.update_positions(1.0)

        # Record velocities
        vel2 = car2.velocity
        vel3 = car3.velocity

        # Advance more time
        self.queue.update_positions(1.0)

        # Car2 should be influenced by car1's movement
        self.assertGreater(
            car2.velocity, vel2, "Car2 should accelerate due to car1's movement"
        )

        # Car3 should be influenced by car2's acceleration
        self.assertGreater(
            car3.velocity, vel3, "Car3 should accelerate due to car2's movement"
        )

    def test_time_multiplier_effect(self):
        """Test that time multipliers affect physics updates."""
        from cascabel.models.simulation import Simulation
        from cascabel.models.models import SimulationConfig

        # Create simulation with time multiplier
        sim_config = SimulationConfig(
            max_simulation_time=10.0,
            time_factor=2.0,  # 2x speed
            enable_telemetry=False,
            enable_position_tracking=False,
        )

        border_config = MagicMock()
        border_config.num_queues = 1
        border_config.nodes_per_queue = [1]
        border_config.arrival_rate = 0
        border_config.service_rates = [1.0]
        border_config.safe_distance = self.safe_distance

        with patch("cascabel.models.simulation.BorderCrossing"):
            sim = Simulation(self.mock_waitline, border_config, sim_config)

            # Advance time
            dt = sim.advance_time()

            # Should return time_factor value
            self.assertEqual(dt, 2.0, "Time multiplier should affect time step")
