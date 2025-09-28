import numpy as np


class ServiceProcess:
    """
    Service Process for Car Queue Simulation
    =======================================

    Generates service times following exponential distribution.
    Service time represents time to process a car through the border crossing.
    Now supports data-driven rates from CBP RSS feeds.
    """

    def __init__(self, service_rate, service_time_variation=0.2, cbp_parser=None):
        """
        Initialize service process.

        Args:
            service_rate: Average service completions per unit time
                          (cars per minute)
            service_time_variation: Coefficient of variation for service times
            cbp_parser: CBPFeedParser instance for real-time data (optional)
        """
        self.base_service_rate = service_rate  # μ (mu) - cars per minute
        self.mean_service_time = 1.0 / service_rate  # minutes
        self.service_time_variation = service_time_variation
        self.cbp_parser = cbp_parser

    @property
    def service_rate(self):
        """Get current service rate, adjusted by CBP data if available."""
        if self.cbp_parser:
            # Use CBP data to adjust base rate
            try:
                avg_wait = self.cbp_parser.get_average_wait_time(
                    "us_mexico", "southbound"
                )
                if avg_wait > 45:  # Very high congestion - slow down processing
                    adjustment_factor = 0.7
                elif avg_wait > 30:  # High congestion
                    adjustment_factor = 0.8
                elif avg_wait > 15:  # Moderate congestion
                    adjustment_factor = 0.9
                else:  # Normal conditions
                    adjustment_factor = 1.0
                return self.base_service_rate * adjustment_factor
            except Exception:
                pass  # Fall back to base rate
        return self.base_service_rate

    def generate_service_time(self):
        """
        Generate service time for a car (exponential distribution).

        Returns:
            Service time in minutes
        """
        return np.random.exponential(self.mean_service_time)

    def generate_variable_service_time(self):
        """
        Generate service time with additional variation.

        Returns:
            Service time in minutes with extra variability
        """
        base_time = self.generate_service_time()
        variation = np.random.normal(0, self.service_time_variation)
        # Ensure positive service time
        return max(0.1, base_time + variation)

    def get_service_rate_at_time(self, time_of_day_hour, queue_length=0):
        """
        Get service rate based on time of day and queue conditions.

        Args:
            time_of_day_hour: Hour (0-23)
            queue_length: Current queue length

        Returns:
            Service rate (cars/minute)
        """
        # Base rate varies by time of day
        if 6 <= time_of_day_hour < 9:  # morning rush - slower processing
            base_rate = 0.8
        elif 16 <= time_of_day_hour < 19:  # evening rush - slower processing
            base_rate = 0.7
        elif 22 <= time_of_day_hour or time_of_day_hour < 4:  # night - faster
            base_rate = 1.2
        else:  # normal hours
            base_rate = 1.0

        # Reduce efficiency with long queues (officer fatigue/stress)
        if queue_length > 20:
            base_rate *= 0.8
        elif queue_length > 10:
            base_rate *= 0.9

        # Adjust with CBP data if available
        if self.cbp_parser:
            try:
                avg_wait = self.cbp_parser.get_average_wait_time(
                    "us_mexico", "southbound"
                )
                if avg_wait > 30:  # High congestion
                    base_rate *= 0.8
                elif avg_wait > 15:  # Moderate congestion
                    base_rate *= 0.9
            except Exception:
                pass

        return base_rate

    def generate_service_time_with_conditions(self, time_of_day_hour, queue_length=0):
        """
        Generate service time considering time of day and queue conditions.

        Args:
            time_of_day_hour: Current hour
            queue_length: Current queue length

        Returns:
            Service time in minutes
        """
        current_rate = self.get_service_rate_at_time(time_of_day_hour, queue_length)
        mean_time = 1.0 / current_rate
        return np.random.exponential(mean_time)
