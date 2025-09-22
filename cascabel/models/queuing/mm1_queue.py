import numpy as np
from datetime import timedelta
from .arrival_process import ArrivalProcess
from .service_process import ServiceProcess


class MM1Queue:
    """
    M/M/1 Queue Model for Car Border Crossing Simulation
    ===================================================

    Implements classic M/M/1 queuing theory with Poisson arrivals
    and exponential service times.
    """

    def __init__(self, arrival_rate, service_rate, max_queue_length=50):
        """
        Initialize M/M/1 queue.

        Args:
            arrival_rate: Average arrival rate (cars/minute)
            service_rate: Average service rate (cars/minute)
            max_queue_length: Maximum cars allowed in queue
        """
        self.arrival_process = ArrivalProcess(arrival_rate)
        self.service_process = ServiceProcess(service_rate)
        self.max_queue_length = max_queue_length

        # Queue state
        self.queue = []  # List of cars in queue
        self.arrival_times = []
        self.service_start_times = []
        self.departure_times = []

        # Statistics
        self.total_arrivals = 0
        self.total_departures = 0
        self.balked_cars = 0  # Cars that couldn't join queue

        # Current state
        self.current_time = 0.0
        self.server_busy = False

    @property
    def utilization(self):
        """Calculate current server utilization ρ = λ/μ"""
        return self.arrival_process.arrival_rate / self.service_process.service_rate

    @property
    def queue_length(self):
        """Current number of cars in queue"""
        return len(self.queue)

    @property
    def is_stable(self):
        """Check if queue is stable (ρ < 1)"""
        return self.utilization < 1.0

    def theoretical_average_queue_length(self):
        """Calculate theoretical average queue length L = ρ/(1-ρ)"""
        if not self.is_stable:
            return float('inf')
        rho = self.utilization
        return rho / (1 - rho)

    def theoretical_average_waiting_time(self):
        """Calculate theoretical average waiting time W = 1/(μ-λ)"""
        if not self.is_stable:
            return float('inf')
        return 1.0 / (self.service_process.service_rate - self.arrival_process.arrival_rate)

    def add_car(self, car, arrival_time):
        """
        Add a car to the queue.

        Args:
            car: Car object
            arrival_time: Arrival timestamp

        Returns:
            True if car was added, False if queue full (balking)
        """
        if len(self.queue) >= self.max_queue_length:
            self.balked_cars += 1
            car.set_status("balked", arrival_time)
            return False

        self.queue.append(car)
        self.arrival_times.append(arrival_time)
        self.total_arrivals += 1
        car.set_status("queued", arrival_time)

        return True

    def process_next_car(self, current_time):
        """
        Process the next car in queue.

        Args:
            current_time: Current simulation time

        Returns:
            Dict with processing info or None if no cars
        """
        if not self.queue:
            self.server_busy = False
            return None

        car = self.queue.pop(0)
        arrival_time = self.arrival_times.pop(0)

        # Calculate waiting time
        waiting_time = (current_time - arrival_time).total_seconds() / 60  # minutes

        # Generate service time
        service_time = self.service_process.generate_service_time()

        self.service_start_times.append(current_time)
        departure_time = current_time + timedelta(minutes=service_time)
        self.departure_times.append(departure_time)

        car.set_status("serving", current_time)

        self.server_busy = True
        self.total_departures += 1

        return {
            'car': car,
            'arrival_time': arrival_time,
            'waiting_time': waiting_time,
            'service_time': service_time,
            'departure_time': departure_time
        }

    def get_queue_statistics(self):
        """
        Calculate current queue statistics.

        Returns:
            Dict with queue metrics
        """
        if not self.departure_times:
            avg_waiting_time = 0.0
        else:
            waiting_times = []
            for i, start_time in enumerate(self.service_start_times):
                arrival_time = self.arrival_times[i] if i < len(self.arrival_times) else start_time
                waiting_times.append((start_time - arrival_time).total_seconds() / 60)
            avg_waiting_time = np.mean(waiting_times) if waiting_times else 0.0

        return {
            'current_queue_length': self.queue_length,
            'total_arrivals': self.total_arrivals,
            'total_departures': self.total_departures,
            'balked_cars': self.balked_cars,
            'server_utilization': self.utilization,
            'average_waiting_time': avg_waiting_time,
            'theoretical_avg_queue_length': self.theoretical_average_queue_length(),
            'theoretical_avg_waiting_time': self.theoretical_average_waiting_time(),
            'is_stable': self.is_stable
        }

    def reset(self):
        """Reset queue to initial state"""
        self.queue.clear()
        self.arrival_times.clear()
        self.service_start_times.clear()
        self.departure_times.clear()
        self.total_arrivals = 0
        self.total_departures = 0
        self.balked_cars = 0
        self.server_busy = False