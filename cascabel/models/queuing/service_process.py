import numpy as np


class ServiceProcess:
    """
    Service Process for Car Queue Simulation
    =======================================

    Generates service times following exponential distribution.
    Service time represents time to process a car through the border crossing.
    """

    def __init__(self, service_rate, service_time_variation=0.2):
        """
        Initialize service process.

        Args:
            service_rate: Average service completions per unit time (cars per minute)
            service_time_variation: Coefficient of variation for service times
        """
        self.service_rate = service_rate  # μ (mu) - cars per minute
        self.mean_service_time = 1.0 / service_rate  # minutes
        self.service_time_variation = service_time_variation

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