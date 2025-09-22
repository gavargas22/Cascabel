import numpy as np
from .car import Car
from .queuing.mm1_queue import MM1Queue
from .models import QueueState, QueueStats


class CarQueue:
    """
    Multi-Car Queue Management
    ==========================

    Manages multiple cars in a queue with realistic following distances,
    arrival/service processes, and queue dynamics.
    """

    def __init__(self, waitline, arrival_rate=2.0, service_rate=3.0,
                 max_queue_length=50, safe_distance=10.0):
        """
        Initialize car queue.

        Args:
            waitline: WaitLine object defining the queue path
            arrival_rate: Average cars per minute (0 if handled centrally)
            service_rate: Average service completions per minute
            max_queue_length: Maximum cars allowed in queue
            safe_distance: Minimum safe distance between cars (meters)
        """
        self.waitline = waitline
        self.safe_distance = safe_distance

        # Initialize queuing theory model (skip if arrival_rate is 0)
        if arrival_rate > 0:
            self.mm1_queue = MM1Queue(
                arrival_rate, service_rate, max_queue_length
            )
        else:
            self.mm1_queue = None

        # Car management
        self.cars = {}  # car_id -> Car object
        self.car_positions = []  # Ordered list of car positions along queue
        self.next_car_id = 1

        # Queue state
        self.serving_car = None  # Car currently being served
        self.service_nodes = []  # Service nodes assigned to this queue

    def add_car(self, sampling_rate=10, phone_config=None):
        """
        Add a new car to the queue.

        Returns:
            Car: The newly created car object
        """
        max_length = self.mm1_queue.max_queue_length if self.mm1_queue else 50
        if len(self.cars) >= max_length:
            return None  # Queue full

        car_id = self.next_car_id
        self.next_car_id += 1

        # Create car at queue entrance
        car = Car(car_id, sampling_rate, phone_config, initial_position=0.0)
        self.cars[car_id] = car

        # Initialize telemetry generator if phone config provided
        if phone_config:
            car.set_telemetry_generator(self.waitline)

        # Add to position tracking
        self.car_positions.append(car_id)

        # Update queue statistics
        if self.mm1_queue:
            self.mm1_queue.total_arrivals += 1

        return car

    def remove_car(self, car_id):
        """
        Remove a car from the queue (completed service).

        Args:
            car_id: ID of car to remove
        """
        if car_id in self.cars:
            car = self.cars[car_id]
            current_time = self.mm1_queue.current_time if self.mm1_queue else 0
            car.set_status("completed", current_time)

            # Remove from tracking
            del self.cars[car_id]
            if car_id in self.car_positions:
                self.car_positions.remove(car_id)

            # Update queue statistics
            if self.mm1_queue:
                self.mm1_queue.total_departures += 1
                self.mm1_queue.departure_times.append(
                    self.mm1_queue.current_time
                )

            # Clear serving car if this was it
            if self.serving_car and self.serving_car.car_id == car_id:
                self.serving_car = None

    def update_positions(self, dt):
        """
        Update positions of all cars in queue based on queue dynamics.

        Args:
            dt: Time step (seconds)
        """
        if not self.car_positions:
            return

        # Sort cars by position (closest to front first)
        sorted_cars = sorted(self.cars.values(), key=lambda c: c.position)

        # Update each car's target velocity based on position in queue
        for i, car in enumerate(sorted_cars):
            if i == 0 and self.serving_car == car:
                # First car being served - can move at service speed
                target_velocity = 5.0  # m/s, constant service speed
            elif i == 0:
                # First car waiting to be served
                target_velocity = 0.0
            else:
                # Following cars maintain safe distance
                front_car = sorted_cars[i-1]
                distance_to_front = (front_car.position - car.position -
                                     front_car.length)

                if distance_to_front > self.safe_distance:
                    # Can speed up
                    target_velocity = min(car.max_velocity,
                                          front_car.velocity * 1.1)
                elif distance_to_front < self.safe_distance * 0.8:
                    # Too close, slow down
                    target_velocity = max(0, front_car.velocity * 0.9)
                else:
                    # Maintain speed
                    target_velocity = front_car.velocity

            # Update car physics
            car.update_physics(target_velocity, dt)

    def start_service(self):
        """
        Start serving the next car in queue.
        """
        if not self.serving_car and self.car_positions:
            # Get first car in queue
            first_car_id = self.car_positions[0]
            first_car = self.cars[first_car_id]

            # Start service
            current_time = self.mm1_queue.current_time if self.mm1_queue else 0
            first_car.set_status("serving", current_time)
            self.serving_car = first_car

            # Generate service time and set completion time
            if self.mm1_queue:
                service_time_minutes = (
                    self.mm1_queue.service_process.generate_service_time()
                )
                self.service_completion_time = (
                    self.mm1_queue.current_time + service_time_minutes * 60
                )

                # Record service start
                self.mm1_queue.service_start_times.append(
                    self.mm1_queue.current_time)

    def advance_time(self, dt):
        """
        Advance simulation time and process queue events.

        Args:
            dt: Time step (seconds)
        """
        if self.mm1_queue:
            self.mm1_queue.current_time += dt

            # Process arrivals (only if not handled centrally)
            while self.mm1_queue.current_time >= self.next_arrival_time:
                self.add_car()
                self.mm1_queue.arrival_times.append(
                    self.mm1_queue.current_time
                )
                # Schedule next arrival
                interarrival_minutes = (
                    self.mm1_queue.arrival_process.generate_interarrival_time()
                )
                self.next_arrival_time += interarrival_minutes * 60

            # Process service completions
            if (self.serving_car and self.service_completion_time and
                    self.mm1_queue.current_time >= self.service_completion_time):
                self.remove_car(self.serving_car.car_id)
                self.service_completion_time = None
                self.start_service()

        # Update car positions
        self.update_positions(dt)

    def get_queue_statistics(self, queue_id):
        """
        Get current queue statistics as Pydantic model.

        Args:
            queue_id: ID of this queue

        Returns:
            QueueStats: Queue statistics
        """
        utilization = self.mm1_queue.utilization if self.mm1_queue else 0.0
        busy_nodes = sum(1 for node in self.service_nodes if node.is_busy)
        total_arrivals = (
            self.mm1_queue.total_arrivals
            if self.mm1_queue else len(self.cars)
        )
        total_completions = (
            self.mm1_queue.total_departures
            if self.mm1_queue else 0
        )

        return QueueStats(
            queue_id=queue_id,
            total_cars=len(self.cars),
            queue_length=len(self.car_positions),
            busy_nodes=busy_nodes,
            num_service_nodes=len(self.service_nodes),
            utilization=utilization,
            average_wait_time=float(self._calculate_average_wait_time()),
            total_arrivals=total_arrivals,
            total_completions=total_completions
        )

    def _calculate_average_wait_time(self):
        """Calculate average waiting time for completed cars."""
        if not self.mm1_queue or not self.mm1_queue.departure_times:
            return 0.0

        wait_times = []
        for i, departure_time in enumerate(self.mm1_queue.departure_times):
            if i < len(self.mm1_queue.arrival_times):
                arrival_time = self.mm1_queue.arrival_times[i]
                wait_times.append(departure_time - arrival_time)

        return np.mean(wait_times) if wait_times else 0.0

    def get_state(self, queue_id):
        """
        Get current queue state as Pydantic model.

        Args:
            queue_id: ID of this queue

        Returns:
            QueueState: Current queue state
        """
        busy_nodes = sum(1 for node in self.service_nodes if node.is_busy)
        total_arrivals = (
            self.mm1_queue.total_arrivals
            if self.mm1_queue else len(self.cars)
        )
        total_completions = (
            self.mm1_queue.total_departures
            if self.mm1_queue else 0
        )

        return QueueState(
            queue_id=queue_id,
            total_cars=len(self.cars),
            queue_length=len(self.car_positions),
            busy_nodes=busy_nodes,
            num_service_nodes=len(self.service_nodes),
            total_arrivals=total_arrivals,
            total_completions=total_completions
        )

    def __repr__(self):
        serving_id = (self.serving_car.car_id if self.serving_car else None)
        return f"CarQueue(cars={len(self.cars)}, serving={serving_id})"