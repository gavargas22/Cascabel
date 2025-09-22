import numpy as np
from datetime import datetime, timedelta


class ArrivalProcess:
    """
    Poisson Arrival Process for Car Queue Simulation
    ===============================================

    Generates car arrival times following exponential interarrival distribution.
    """

    def __init__(self, arrival_rate):
        """
        Initialize arrival process.

        Args:
            arrival_rate: Average arrivals per unit time (cars per minute)
        """
        self.arrival_rate = arrival_rate  # λ (lambda) - cars per minute
        self.mean_interarrival_time = 1.0 / arrival_rate  # minutes

    def generate_interarrival_time(self):
        """
        Generate time until next car arrives (exponential distribution).

        Returns:
            Interarrival time in minutes
        """
        return np.random.exponential(self.mean_interarrival_time)

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

        while (current_time - start_time).total_seconds() / 60 < simulation_duration_minutes:
            interarrival = self.generate_interarrival_time()
            current_time += timedelta(minutes=interarrival)

            if (current_time - start_time).total_seconds() / 60 < simulation_duration_minutes:
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
        # Typical border crossing patterns
        if 6 <= time_of_day_hour < 9:  # morning rush
            return 1.5
        elif 16 <= time_of_day_hour < 19:  # evening rush
            return 1.8
        elif 22 <= time_of_day_hour or time_of_day_hour < 4:  # night
            return 0.2
        else:  # off-peak
            return 0.5

    def generate_time_varying_arrivals(self, simulation_duration_minutes, start_time=None):
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

        while (current_time - start_time).total_seconds() / 60 < simulation_duration_minutes:
            # Get current hour for rate adjustment
            current_hour = current_time.hour
            current_rate = self.get_arrival_rate_at_time(current_hour)

            # Generate interarrival time with current rate
            interarrival = np.random.exponential(1.0 / current_rate)
            current_time += timedelta(minutes=interarrival)

            if (current_time - start_time).total_seconds() / 60 < simulation_duration_minutes:
                arrival_times.append(current_time)

        return arrival_times