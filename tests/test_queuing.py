import unittest
import numpy as np
from datetime import datetime, timedelta
from cascabel.models.queuing.mm1_queue import MM1Queue
from cascabel.models.queuing.arrival_process import ArrivalProcess
from cascabel.models.queuing.service_process import ServiceProcess
from cascabel.models.car import Car
from cascabel.utils.rss_feed import CBPFeedParser, BorderWaitTime


class TestArrivalProcess(unittest.TestCase):
    """Test cases for Poisson arrival process."""

    def setUp(self):
        self.arrival_rate = 2.0  # cars per minute
        self.arrival_process = ArrivalProcess(self.arrival_rate)

    def test_initialization(self):
        """Test arrival process initialization."""
        self.assertEqual(self.arrival_process.arrival_rate, self.arrival_rate)
        self.assertEqual(self.arrival_process.mean_interarrival_time, 0.5)

    def test_generate_interarrival_time(self):
        """Test interarrival time generation."""
        # Test multiple samples
        times = [
            self.arrival_process.generate_interarrival_time(12 * 3600)  # Noon
            for _ in range(1000)
        ]

        # Should follow exponential distribution
        mean_time = np.mean(times)
        # Allow some statistical variation
        self.assertAlmostEqual(mean_time, 0.5, delta=0.1)

        # All times should be positive
        self.assertTrue(all(t > 0 for t in times))

    def test_generate_arrival_times(self):
        """Test arrival time generation over a period."""
        duration = 10  # minutes
        start_time = datetime(2025, 1, 1, 8, 0, 0)
        arrival_times = self.arrival_process.generate_arrival_times(
            duration, start_time
        )

        # Should have approximately correct number of arrivals
        expected_arrivals = self.arrival_rate * duration
        self.assertAlmostEqual(len(arrival_times), expected_arrivals, delta=12)

        # All times should be within the duration
        for arrival_time in arrival_times:
            elapsed = (arrival_time - start_time).total_seconds() / 60
            self.assertLess(elapsed, duration)

    def test_time_varying_arrival_rate(self):
        """Test time-varying arrival rates."""
        # Morning rush hour
        rate_8am = self.arrival_process.get_arrival_rate_at_time(8)
        self.assertEqual(rate_8am, 1.5)

        # Evening rush hour
        rate_6pm = self.arrival_process.get_arrival_rate_at_time(18)
        self.assertEqual(rate_6pm, 1.8)

        # Night time
        rate_2am = self.arrival_process.get_arrival_rate_at_time(2)
        self.assertEqual(rate_2am, 0.2)

        # Off-peak
        rate_10am = self.arrival_process.get_arrival_rate_at_time(10)
        self.assertEqual(rate_10am, 2.0)

    def test_generate_time_varying_arrivals(self):
        """Test generation of time-varying arrivals."""
        duration = 60  # 1 hour
        start_time = datetime(2025, 1, 1, 6, 0, 0)  # Start at 6 AM
        arrival_times = self.arrival_process.generate_time_varying_arrivals(
            duration, start_time
        )

        # Should generate some arrivals
        self.assertGreater(len(arrival_times), 0)

        # All times should be within duration
        for arrival_time in arrival_times:
            elapsed = (arrival_time - start_time).total_seconds() / 60
            self.assertLess(elapsed, duration)


class TestServiceProcess(unittest.TestCase):
    """Test cases for service process."""

    def setUp(self):
        self.service_rate = 3.0  # cars per minute
        self.service_process = ServiceProcess(self.service_rate)

    def test_initialization(self):
        """Test service process initialization."""
        self.assertEqual(self.service_process.service_rate, self.service_rate)
        mean_time = 1.0 / self.service_rate
        self.assertEqual(self.service_process.mean_service_time, mean_time)

    def test_generate_service_time(self):
        """Test service time generation."""
        times = [self.service_process.generate_service_time() for _ in range(1000)]

        # Should follow exponential distribution
        mean_time = np.mean(times)
        expected_mean = 1.0 / self.service_rate
        self.assertAlmostEqual(mean_time, expected_mean, delta=0.1)

        # All times should be positive
        self.assertTrue(all(t > 0 for t in times))

    def test_generate_variable_service_time(self):
        """Test variable service time generation."""
        times = [
            self.service_process.generate_variable_service_time() for _ in range(1000)
        ]

        # Should still be positive
        self.assertTrue(all(t > 0 for t in times))

        # Should have some variation
        std_time = np.std(times)
        self.assertGreater(std_time, 0)

    def test_generate_service_time_with_conditions(self):
        """Test service time generation with conditions."""
        time_normal = self.service_process.generate_service_time_with_conditions(10, 0)
        self.assertGreater(time_normal, 0)

        time_rush = self.service_process.generate_service_time_with_conditions(8, 25)
        self.assertGreater(time_rush, 0)


class TestMM1Queue(unittest.TestCase):
    """Test cases for M/M/1 queue model."""

    def setUp(self):
        self.arrival_rate = 2.0  # cars/minute
        self.service_rate = 3.0  # cars/minute
        self.queue = MM1Queue(self.arrival_rate, self.service_rate, max_queue_length=10)

    def test_initialization(self):
        """Test queue initialization."""
        self.assertEqual(self.queue.arrival_process.arrival_rate, self.arrival_rate)
        self.assertEqual(self.queue.service_process.service_rate, self.service_rate)
        self.assertEqual(self.queue.max_queue_length, 10)
        self.assertEqual(self.queue.queue_length, 0)
        self.assertFalse(self.queue.server_busy)

    def test_utilization(self):
        """Test server utilization calculation."""
        expected_utilization = self.arrival_rate / self.service_rate
        self.assertEqual(self.queue.utilization, expected_utilization)

    def test_stability(self):
        """Test queue stability check."""
        # Stable queue (ρ < 1)
        stable_queue = MM1Queue(2.0, 3.0)
        self.assertTrue(stable_queue.is_stable)

        # Unstable queue (ρ > 1)
        unstable_queue = MM1Queue(3.0, 2.0)
        self.assertFalse(unstable_queue.is_stable)

    def test_theoretical_metrics(self):
        """Test theoretical queue metrics."""
        # Stable queue
        rho = self.arrival_rate / self.service_rate
        expected_avg_queue_length = rho / (1 - rho)
        expected_avg_waiting_time = 1.0 / (self.service_rate - self.arrival_rate)

        self.assertAlmostEqual(
            self.queue.theoretical_average_queue_length(),
            expected_avg_queue_length,
            places=5,
        )
        self.assertAlmostEqual(
            self.queue.theoretical_average_waiting_time(),
            expected_avg_waiting_time,
            places=5,
        )

        # Unstable queue should return infinity
        unstable_queue = MM1Queue(3.0, 2.0)
        self.assertEqual(
            unstable_queue.theoretical_average_queue_length(), float("inf")
        )
        self.assertEqual(
            unstable_queue.theoretical_average_waiting_time(), float("inf")
        )

    def test_add_car(self):
        """Test adding cars to queue."""
        car1 = Car(1, 10, None)
        car2 = Car(2, 10, None)

        # Add first car
        result1 = self.queue.add_car(car1, datetime.now())
        self.assertTrue(result1)
        self.assertEqual(self.queue.queue_length, 1)
        self.assertEqual(self.queue.total_arrivals, 1)

        # Add second car
        result2 = self.queue.add_car(car2, datetime.now())
        self.assertTrue(result2)
        self.assertEqual(self.queue.queue_length, 2)
        self.assertEqual(self.queue.total_arrivals, 2)

    def test_queue_full_balking(self):
        """Test balking when queue is full."""
        small_queue = MM1Queue(2.0, 3.0, max_queue_length=2)

        # Fill the queue
        for i in range(3):
            car = Car(i + 1, 10, None)
            result = small_queue.add_car(car, datetime.now())
            if i < 2:
                self.assertTrue(result)
            else:
                self.assertFalse(result)  # Should balk

        self.assertEqual(small_queue.queue_length, 2)
        self.assertEqual(small_queue.total_arrivals, 2)
        self.assertEqual(small_queue.balked_cars, 1)

    def test_process_next_car(self):
        """Test processing cars from queue."""
        car = Car(1, 10, None)
        arrival_time = datetime.now()

        # Add car to queue
        self.queue.add_car(car, arrival_time)

        # Process the car
        current_time = arrival_time + timedelta(minutes=1)
        result = self.queue.process_next_car(current_time)

        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["car"], car)
            self.assertEqual(result["arrival_time"], arrival_time)
            self.assertGreater(result["service_time"], 0)
            self.assertIsInstance(result["departure_time"], datetime)

        # Queue should be empty and server busy
        self.assertEqual(self.queue.queue_length, 0)
        self.assertTrue(self.queue.server_busy)
        self.assertEqual(self.queue.total_departures, 1)

    def test_process_empty_queue(self):
        """Test processing when queue is empty."""
        current_time = datetime.now()
        result = self.queue.process_next_car(current_time)

        self.assertIsNone(result)
        self.assertFalse(self.queue.server_busy)

    def test_queue_statistics(self):
        """Test queue statistics calculation."""
        # Add and process some cars to generate statistics
        for i in range(3):
            car = Car(i + 1, 10, None)
            arrival_time = datetime.now() + timedelta(minutes=i)
            self.queue.add_car(car, arrival_time)

            # Process immediately for simplicity
            process_time = arrival_time + timedelta(minutes=0.1)
            self.queue.process_next_car(process_time)

        stats = self.queue.get_queue_statistics()

        # Check that all expected keys are present
        expected_keys = [
            "current_queue_length",
            "total_arrivals",
            "total_departures",
            "balked_cars",
            "server_utilization",
            "average_waiting_time",
            "theoretical_avg_queue_length",
            "theoretical_avg_waiting_time",
            "is_stable",
        ]

        for key in expected_keys:
            self.assertIn(key, stats)

        # Check specific values
        self.assertEqual(stats["total_arrivals"], 3)
        self.assertEqual(stats["total_departures"], 3)
        self.assertEqual(stats["balked_cars"], 0)
        utilization = self.arrival_rate / self.service_rate
        self.assertEqual(stats["server_utilization"], utilization)
        self.assertTrue(stats["is_stable"])

    def test_reset(self):
        """Test queue reset functionality."""
        # Add some cars and process
        car = Car(1, 10, None)
        self.queue.add_car(car, datetime.now())
        self.queue.process_next_car(datetime.now())

        # Reset
        self.queue.reset()

        # Check everything is reset
        self.assertEqual(self.queue.queue_length, 0)
        self.assertEqual(self.queue.total_arrivals, 0)
        self.assertEqual(self.queue.total_departures, 0)
        self.assertEqual(self.queue.balked_cars, 0)
        self.assertFalse(self.queue.server_busy)
        self.assertEqual(len(self.queue.arrival_times), 0)
        self.assertEqual(len(self.queue.service_start_times), 0)
        self.assertEqual(len(self.queue.departure_times), 0)


class TestCBPFeedParser(unittest.TestCase):
    """Test cases for CBP RSS feed parsing."""

    def setUp(self):
        # Use a long cache duration for testing to avoid fetching
        self.parser = CBPFeedParser(cache_duration_minutes=60)

    def test_initialization(self):
        """Test CBP feed parser initialization."""
        self.assertIsInstance(self.parser.cache_duration, timedelta)
        self.assertEqual(self.parser._last_fetch, {})
        self.assertEqual(self.parser._cached_data, {})

    def test_unknown_border(self):
        """Test error handling for unknown border."""
        with self.assertRaises(ValueError):
            self.parser.fetch_border_wait_times("unknown_border")

    def test_border_wait_time_creation(self):
        """Test BorderWaitTime dataclass creation."""
        now = datetime.now()
        wait_time = BorderWaitTime(
            port_name="San Ysidro",
            border_name="US-Mexico Border",
            crossing_name="San Ysidro",
            port_number="250401",
            border="US-Mexico Border",
            direction="southbound",
            date=now,
            delay_minutes=30,
            lanes_open=5,
            update_time=now,
        )

        self.assertEqual(wait_time.port_name, "San Ysidro")
        self.assertEqual(wait_time.delay_minutes, 30)
        self.assertTrue(wait_time.is_us_mexico_border)
        self.assertTrue(wait_time.is_southbound)

    def test_extract_port_number(self):
        """Test port number extraction from description."""
        description = "Port: 250401, Delay: 30 minutes"
        port_number = self.parser._extract_port_number(description)
        self.assertEqual(port_number, "250401")

    def test_extract_delay(self):
        """Test delay extraction from description."""
        # Test "Delay: X minutes" format
        desc1 = "Delay: 45 minutes, Lanes: 3"
        delay1 = self.parser._extract_delay(desc1)
        self.assertEqual(delay1, 45)

        # Test "X minute delay" format
        desc2 = "There is a 20 minute delay at this crossing."
        delay2 = self.parser._extract_delay(desc2)
        self.assertEqual(delay2, 20)

        # Test no delay
        desc3 = "No delay reported"
        delay3 = self.parser._extract_delay(desc3)
        self.assertEqual(delay3, 0)

    def test_extract_lanes(self):
        """Test lanes extraction from description."""
        # Test "Lanes: X" format
        desc1 = "Lanes: 4, Delay: 15 minutes"
        lanes1 = self.parser._extract_lanes(desc1)
        self.assertEqual(lanes1, 4)

        # Test "X lanes" format
        desc2 = "5 lanes are open for processing"
        lanes2 = self.parser._extract_lanes(desc2)
        self.assertEqual(lanes2, 5)

        # Test default
        desc3 = "No lane information"
        lanes3 = self.parser._extract_lanes(desc3)
        self.assertEqual(lanes3, 1)

    def test_get_average_wait_time(self):
        """Test average wait time calculation."""
        # Mock some wait times
        now = datetime.now()
        mock_wait_times = [
            BorderWaitTime(
                port_name="San Ysidro",
                border_name="US-Mexico Border",
                crossing_name="San Ysidro",
                port_number="250401",
                border="US-Mexico Border",
                direction="southbound",
                date=now,
                delay_minutes=30,
                lanes_open=5,
                update_time=now,
            ),
            BorderWaitTime(
                port_name="Tijuana",
                border_name="US-Mexico Border",
                crossing_name="Tijuana",
                port_number="250402",
                border="US-Mexico Border",
                direction="southbound",
                date=now,
                delay_minutes=45,
                lanes_open=3,
                update_time=now,
            ),
            BorderWaitTime(
                port_name="Tecate",
                border_name="US-Mexico Border",
                crossing_name="Tecate",
                port_number="250403",
                border="US-Mexico Border",
                direction="northbound",
                date=now,
                delay_minutes=20,
                lanes_open=2,
                update_time=now,
            ),
        ]

        # Temporarily replace cached data
        self.parser._cached_data["us_mexico_border"] = mock_wait_times
        self.parser._last_fetch["us_mexico_border"] = datetime.now()

        # Test southbound average
        avg_south = self.parser.get_average_wait_time("us_mexico", "southbound")
        expected_south = (30 + 45) / 2  # 37.5
        self.assertAlmostEqual(avg_south, expected_south, places=1)

        # Test northbound average
        avg_north = self.parser.get_average_wait_time("us_mexico", "northbound")
        self.assertEqual(avg_north, 20.0)

    def test_get_port_wait_time(self):
        """Test specific port wait time retrieval."""
        now = datetime.now()
        mock_wait_times = [
            BorderWaitTime(
                port_name="San Ysidro",
                border_name="US-Mexico Border",
                crossing_name="San Ysidro",
                port_number="250401",
                border="US-Mexico Border",
                direction="southbound",
                date=now,
                delay_minutes=30,
                lanes_open=5,
                update_time=now,
            )
        ]

        self.parser._cached_data["us_mexico_border"] = mock_wait_times
        self.parser._last_fetch["us_mexico_border"] = datetime.now()

        # Test existing port
        wait_time = self.parser.get_port_wait_time("San Ysidro", "us_mexico")
        self.assertEqual(wait_time, 30)

        # Test non-existing port
        wait_time_none = self.parser.get_port_wait_time("NonExistent", "us_mexico")
        self.assertIsNone(wait_time_none)

    # Note: We don't test actual RSS fetching in unit tests to avoid
    # network dependencies. Integration tests would cover that.


if __name__ == "__main__":
    unittest.main()
