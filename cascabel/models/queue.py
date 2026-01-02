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

    def __init__(
        self,
        waitline,
        arrival_rate=2.0,
        service_rate=3.0,
        max_queue_length=50,
        safe_distance=10.0,
    ):
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
            self.mm1_queue = MM1Queue(arrival_rate, service_rate, max_queue_length)
        else:
            self.mm1_queue = None

        # Car management
        self.cars = {}  # car_id -> Car object
        self.car_positions = []  # Ordered list of car positions along queue
        self.next_car_id = 1

        # Queue state
        self.serving_car = None  # Car currently being served
        self.service_nodes = []  # Service nodes assigned to this queue

    def add_car(self, car_id=None, sampling_rate=10, phone_config=None):
        """
        Add a new car to the queue.

        Args:
            car_id: Unique ID for the car (if None, uses internal counter)
            sampling_rate: Telemetry sampling rate
            phone_config: Phone configuration for telemetry

        Returns:
            Car: The newly created car object
        """
        max_length = self.mm1_queue.max_queue_length if self.mm1_queue else 50
        if len(self.cars) >= max_length:
            return None  # Queue full

        # Use provided car_id or generate one
        if car_id is None:
            car_id = self.next_car_id
            self.next_car_id += 1

        # Create car at the START of the linestring (far from booth)
        # Position 0 = north end of linestring (start)
        # Position max = south end of linestring (booth)
        # They will travel toward position max (increasing position toward booth)
        initial_position = 0.0  # Start at beginning of linestring (north)
        car = Car(car_id, sampling_rate, phone_config, initial_position=initial_position)
        car.status = "approaching"  # Start in approaching state
        car.velocity = 0.0  # Start from stationary, will accelerate to approach speed
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
                self.mm1_queue.departure_times.append(self.mm1_queue.current_time)

            # Clear serving car if this was it
            if self.serving_car and self.serving_car.car_id == car_id:
                self.serving_car = None

    def get_control_point_speed_limit(self, position, traffic_control_points, default_speed):
        """
        Calculate speed limit at a given position based on traffic control points.

        Args:
            position: Current position along the linestring (meters)
            traffic_control_points: List of control point definitions
            default_speed: Speed to use if no control points apply

        Returns:
            float: Target speed in m/s
        """
        if not traffic_control_points:
            return default_speed

        # Check each control point
        for cp in traffic_control_points:
            cp_position = cp.get('position_meters', 0)

            if cp['type'] == 'sensor_array':
                # Sensor arrays slow down traffic in a zone
                slowdown_start = cp_position - cp.get('slowdown_distance_meters', 30)
                slowdown_end = cp_position + cp.get('slowdown_distance_meters', 30)

                if slowdown_start <= position <= slowdown_end:
                    # Inside slowdown zone - use target speed
                    target_speed = cp.get('target_speed_mps', 2.24)  # default 5 mph
                    return target_speed
                elif position < slowdown_start and (slowdown_start - position) < 20:
                    # Approaching slowdown zone - start reducing speed
                    distance_to_zone = slowdown_start - position
                    # Linear interpolation from default_speed to target_speed
                    target_speed = cp.get('target_speed_mps', 2.24)
                    blend = distance_to_zone / 20.0
                    return target_speed + (default_speed - target_speed) * blend

            elif cp['type'] == 'booth':
                # Booths cause complete stops - handled separately in queue logic
                # Just check if we're approaching the booth
                stop_distance = cp.get('stop_distance_meters', 40)
                if position >= (cp_position - stop_distance):
                    # Very close to booth - should be in queue already
                    return 0.0

        return default_speed

    def update_positions(self, dt):
        """
        Update positions of all cars in queue based on queue dynamics.

        Args:
            dt: Time step (seconds)
        """
        if not self.car_positions:
            return

        # Sort cars by position (front of queue first - HIGHEST position number)
        # Position increases as cars approach the booth (toward waitline_length)
        sorted_cars = sorted(self.cars.values(), key=lambda c: c.position, reverse=True)

        booth_position = self.waitline.waitline_length if self.waitline else 1000.0

        # Get traffic control points from waitline
        traffic_control_points = self.waitline.traffic_control_points if self.waitline else []

        # Update each car's target velocity based on position in queue
        for i, car in enumerate(sorted_cars):
            # Assign each car a preferred speed with variance (27-33 mph range)
            if not hasattr(car, 'preferred_speed'):
                speed_variance = np.random.uniform(0.9, 1.1)
                car.preferred_speed = car.max_velocity * speed_variance

            # Handle approaching cars (moving toward booth)
            if car.status == "approaching":
                # Check if car has reached the queue (close to booth)
                if car.position >= (booth_position - self.safe_distance):
                    # Transition to queued
                    car.status = "queued"
                    current_time = self.mm1_queue.current_time if self.mm1_queue else 0
                    car.set_status("queued", current_time)
                    target_velocity = 0.0  # Stop at queue
                else:
                    # Check distance to booth and car ahead
                    distance_to_booth = booth_position - car.position

                    # Apply traffic control point speed limits
                    control_speed_limit = self.get_control_point_speed_limit(
                        car.position, traffic_control_points, car.preferred_speed
                    )

                    # Check if there's a car ahead (car in front has higher position, which is at lower index)
                    if i > 0:
                        front_car = sorted_cars[i - 1]  # Car ahead (higher position)
                        distance_to_front = front_car.position - car.position - front_car.length

                        # Car-following behavior with control point limits
                        if distance_to_front < self.safe_distance * 2:
                            # Getting close - slow down to match or below front car
                            target_velocity = min(front_car.velocity, control_speed_limit * 0.7)
                        elif distance_to_front < self.safe_distance * 3:
                            # Moderate distance - match front car speed but respect control points
                            target_velocity = min(control_speed_limit, front_car.velocity)
                        else:
                            # Safe distance - use control point speed limit or slow down near booth
                            if distance_to_booth < 50:
                                target_velocity = max(car.queue_velocity, control_speed_limit * (distance_to_booth / 50))
                            else:
                                target_velocity = control_speed_limit
                    else:
                        # No car ahead (first car approaching), use control point limits and slow near booth
                        if distance_to_booth < 50:  # Start slowing 50m from booth
                            # Gradual deceleration
                            target_velocity = max(car.queue_velocity, control_speed_limit * (distance_to_booth / 50))
                        else:
                            target_velocity = control_speed_limit

                # Use physics to update (gradual acceleration/deceleration)
                car.update_physics(target_velocity, dt)

            elif i == 0 and self.serving_car == car:
                # First car being served - stationary at booth
                target_velocity = 0.0
                car.position = booth_position  # Keep at booth
            elif i == 0:
                # First car in queue waiting to be served - stationary
                target_velocity = 0.0
            else:
                # Following cars in queue - move slowly toward car ahead
                front_car = sorted_cars[i - 1]
                distance_to_front = front_car.position - car.position - front_car.length

                # Queue movement behavior - slow crawl forward
                if distance_to_front > self.safe_distance * 1.5:
                    # Gap too large - move forward at queue speed (3 mph)
                    target_velocity = car.queue_velocity
                elif distance_to_front > self.safe_distance:
                    # Normal queue spacing - creep forward slowly
                    target_velocity = car.queue_velocity * 0.5
                elif distance_to_front > self.safe_distance * 0.5:
                    # Getting close - very slow creep
                    target_velocity = car.queue_velocity * 0.3
                else:
                    # Too close - stop
                    target_velocity = 0.0

            # Update car physics (except for approaching cars handled above)
            if car.status != "approaching":
                car.update_physics(target_velocity, dt)

    def start_service(self):
        """
        Start serving the next car in queue.
        """
        if not self.serving_car and self.cars:
            # Get car with highest position (closest to booth = front of queue)
            sorted_cars = sorted(self.cars.values(), key=lambda c: c.position, reverse=True)
            if sorted_cars and sorted_cars[0].status == "queued":
                first_car = sorted_cars[0]

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
                    self.mm1_queue.service_start_times.append(self.mm1_queue.current_time)

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
                self.mm1_queue.arrival_times.append(self.mm1_queue.current_time)
                # Schedule next arrival
                interarrival_minutes = (
                    self.mm1_queue.arrival_process.generate_interarrival_time()
                )
                self.next_arrival_time += interarrival_minutes * 60

            # Process service completions
            if (
                self.serving_car
                and self.service_completion_time
                and self.mm1_queue.current_time >= self.service_completion_time
            ):
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
            self.mm1_queue.total_arrivals if self.mm1_queue else len(self.cars)
        )
        total_completions = self.mm1_queue.total_departures if self.mm1_queue else 0

        return QueueStats(
            queue_id=queue_id,
            total_cars=len(self.cars),
            queue_length=len(self.car_positions),
            busy_nodes=busy_nodes,
            num_service_nodes=len(self.service_nodes),
            utilization=utilization,
            average_wait_time=float(self._calculate_average_wait_time()),
            total_arrivals=total_arrivals,
            total_completions=total_completions,
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
            self.mm1_queue.total_arrivals if self.mm1_queue else len(self.cars)
        )
        total_completions = self.mm1_queue.total_departures if self.mm1_queue else 0

        return QueueState(
            queue_id=queue_id,
            total_cars=len(self.cars),
            queue_length=len(self.car_positions),
            busy_nodes=busy_nodes,
            num_service_nodes=len(self.service_nodes),
            total_arrivals=total_arrivals,
            total_completions=total_completions,
        )

    def __repr__(self):
        serving_id = self.serving_car.car_id if self.serving_car else None
        return f"CarQueue(cars={len(self.cars)}, serving={serving_id})"
