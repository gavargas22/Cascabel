import numpy as np
from datetime import datetime, timedelta


class ArrivalProcess:
    """
    Poisson Arrival Process for Car Queue Simulation
    ===============================================

    Generates car arrival times following exponential interarrival
    distribution. Now supports data-driven rates from CBP RSS feeds.
    """

    def __init__(self, arrival_rate, cbp_parser=None):
        """
        Initialize arrival process.

        Args:
            arrival_rate: Base average arrivals per unit time (cars per minute)
            cbp_parser: CBPFeedParser instance for real-time data (optional)
        """
        self.base_arrival_rate = arrival_rate  # λ (lambda) - cars per minute
        self.mean_interarrival_time = 1.0 / arrival_rate  # minutes
        self.cbp_parser = cbp_parser

    @property
    def arrival_rate(self):
        """Get current arrival rate, adjusted by CBP data if available."""
        rate = self.base_arrival_rate
        if self.cbp_parser:
            # Use CBP data to adjust base rate
            try:
                avg_wait = self.cbp_parser.get_average_wait_time(
                    "us_mexico", "southbound"
                )
                if avg_wait > 0:
                    # Higher wait times suggest higher demand
                    # Scale base rate by wait time factor (capped)
                    adjustment_factor = min(2.0, 1.0 + (avg_wait / 60.0))
                    rate *= adjustment_factor
            except Exception:
                pass  # Fall back to base rate
        return rate

    def get_time_of_day_factor(self, current_time_seconds):
        """
        Get time-of-day adjustment factor for arrival rate.

        Args:
            current_time_seconds: Current simulation time in seconds

        Returns:
            Multiplier for base arrival rate (0.1 to 2.0)
        """
        # Assume simulation starts at midnight
        hour_of_day = (current_time_seconds / 3600) % 24

        # Peak hours: morning rush (7-9), evening rush (16-18)
        if 7 <= hour_of_day < 9:
            return 1.8  # Morning peak
        elif 16 <= hour_of_day < 18:
            return 2.0  # Evening peak
        elif 9 <= hour_of_day < 16:
            return 1.2  # Daytime moderate
        elif 22 <= hour_of_day or hour_of_day < 6:
            return 0.1  # Night low
        else:
            return 0.5  # Off-peak

    def generate_interarrival_time(self, current_time_seconds: float = 0):
        """
        Generate time until next car arrives (exponential distribution).

        Args:
            current_time_seconds: Current simulation time in seconds

        Returns:
            Interarrival time in minutes
        """
        current_rate = self.get_arrival_rate_at_time((current_time_seconds / 3600) % 24)
        if current_rate > 0:
            return np.random.exponential(1.0 / current_rate)
        else:
            return float("inf")  # No arrivals if rate is 0

    def generate_arrival_times(self, simulation_duration_minutes, start_time=None):
        """
        Generate list of arrival times over simulation period.

        Args:
            simulation_duration_minutes: Total simulation time in minutes
            start_time: Simulation start time (datetime)

        Returns:
            List of arrival times (datetime objects)
        """
        if start_time is None:
            start_time = datetime.now()

        arrival_times = []
        current_time = start_time
        start_hour = start_time.hour

        while (
            current_time - start_time
        ).total_seconds() / 60 < simulation_duration_minutes:
            current_seconds = (current_time - start_time).total_seconds()
            simulation_seconds = current_seconds + start_hour * 3600
            interarrival = self.generate_interarrival_time(simulation_seconds)
            current_time += timedelta(minutes=interarrival)

            if (
                current_time - start_time
            ).total_seconds() / 60 < simulation_duration_minutes:
                arrival_times.append(current_time)

        return arrival_times

    def get_arrival_rate_at_time(self, time_of_day_hour):
        """
        Get time-varying arrival rate based on hour of day.

        Args:
            time_of_day_hour: Hour (0-23)

        Returns:
            Arrival rate for that hour (cars/minute)
        """
        # Time-of-day factors
        if 6 <= time_of_day_hour < 9:  # morning rush
            factor = 0.75
        elif 16 <= time_of_day_hour < 19:  # evening rush
            factor = 0.9
        elif 22 <= time_of_day_hour or time_of_day_hour < 4:  # night
            factor = 0.1
        else:  # off-peak
            factor = 1.0

        base_rate = self.base_arrival_rate * factor

        # Adjust with CBP data if available
        if self.cbp_parser:
            try:
                avg_wait = self.cbp_parser.get_average_wait_time(
                    "us_mexico", "southbound"
                )
                if avg_wait > 30:  # High congestion
                    base_rate *= 1.5
                elif avg_wait > 15:  # Moderate congestion
                    base_rate *= 1.2
            except Exception:
                pass

        return base_rate

    def generate_time_varying_arrivals(
        self, simulation_duration_minutes, start_time=None
    ):
        """
        Generate arrivals with time-varying rates.

        Args:
            simulation_duration_minutes: Total simulation time in minutes
            start_time: Simulation start time (datetime)

        Returns:
            List of arrival times (datetime objects)
        """
        if start_time is None:
            start_time = datetime.now()

        arrival_times = []
        current_time = start_time

        while (
            current_time - start_time
        ).total_seconds() / 60 < simulation_duration_minutes:
            # Get current hour for rate adjustment
            current_hour = current_time.hour
            current_rate = self.get_arrival_rate_at_time(current_hour)

            # Generate interarrival time with current rate
            interarrival = np.random.exponential(1.0 / current_rate)
            current_time += timedelta(minutes=interarrival)

            if (
                current_time - start_time
            ).total_seconds() / 60 < simulation_duration_minutes:
                arrival_times.append(current_time)

        return arrival_times

    def get_arrival_rate(self, current_time_seconds=0):
        """
        Get arrival rate adjusted for time-of-day and CBP data.

        Args:
            current_time_seconds: Current simulation time in seconds

        Returns:
            Arrival rate in cars per minute
        """
        rate = self.arrival_rate * self.get_time_of_day_factor(current_time_seconds)
        return rate
