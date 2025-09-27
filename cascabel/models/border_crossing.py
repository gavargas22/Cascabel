import numpy as np
from .queue import CarQueue
from .models import (
    BorderCrossingConfig,
    ServiceNodeState,
    BorderCrossingStats,
    ServiceNodeStats,
)


class ServiceNode:
    """
    Service Node (Booth)
    ====================

    Represents an individual service point that can process cars.
    Each service node has its own service rate and can be busy/idle.
    """

    def __init__(self, node_id, service_rate, service_time_variation=0.2):
        """
        Initialize service node.

        Args:
            node_id: Unique identifier for this service node
            service_rate: Average service completions per minute
            service_time_variation: Coefficient of variation for service times
        """
        self.node_id = node_id
        self.service_rate = service_rate
        self.service_time_variation = service_time_variation

        # Service state
        self.is_busy = False
        self.current_car = None
        self.service_completion_time = None

        # Statistics
        self.total_served = 0
        self.total_service_time = 0.0

    def start_service(self, car, current_time):
        """
        Start serving a car.

        Args:
            car: Car object to serve
            current_time: Current simulation time
        """
        if self.is_busy:
            return False

        self.is_busy = True
        self.current_car = car
        car.set_status("serving", current_time)

        # Generate service time
        service_time_minutes = np.random.exponential(1.0 / self.service_rate)
        self.service_completion_time = current_time + service_time_minutes * 60

        return True

    def complete_service(self, current_time):
        """
        Complete service for current car.

        Returns:
            Car: The completed car, or None if no car was being served
        """
        if not self.is_busy or not self.current_car:
            return None

        car = self.current_car
        service_time = current_time - car.service_start_time
        car.set_status("completed", current_time)

        # Update statistics
        self.total_served += 1
        self.total_service_time += service_time

        # Reset node
        self.is_busy = False
        self.current_car = None
        self.service_completion_time = None

        return car

    def is_available(self):
        """Check if service node is available."""
        return not self.is_busy

    def get_state(self, queue_id) -> ServiceNodeState:
        """
        Get current service node state as Pydantic model.

        Args:
            queue_id: ID of the queue this node belongs to

        Returns:
            ServiceNodeState: Current node state
        """
        return ServiceNodeState(
            node_id=self.node_id,
            queue_id=queue_id,
            is_busy=self.is_busy,
            current_car_id=(self.current_car.car_id if self.current_car else None),
            service_rate=self.service_rate,
            total_served=self.total_served,
            total_service_time=self.total_service_time,
        )

    def __repr__(self):
        status = "busy" if self.is_busy else "idle"
        car_id = self.current_car.car_id if self.current_car else "none"
        return f"ServiceNode(id={self.node_id}, status={status}, car={car_id})"


class BorderCrossing:
    """
    Border Crossing with Multiple Queues and Service Nodes
    ======================================================

    Manages multiple queues feeding into multiple service nodes.
    Supports various queue assignment strategies and service configurations.
    """

    def __init__(self, waitline, config):
        """
        Initialize border crossing.

        Args:
            waitline: WaitLine object defining the path
            config: BorderCrossingConfig object or dict
        """
        self.waitline = waitline

        # Use Pydantic model for configuration
        if isinstance(config, dict):
            self.config = BorderCrossingConfig(**config)
        else:
            self.config = config

        # Initialize queues
        self.queues = []
        self.service_nodes = []
        self._initialize_queues_and_nodes()

        # Car routing
        self.next_queue_index = 0  # For round-robin assignment

        # Arrival timing
        self.next_arrival_time = 0.0
        self.arrival_process = None  # Will be set if config has cbp_parser

        # Statistics
        self.total_arrivals = 0
        self.total_completions = 0
        self.current_time = 0.0

    def _initialize_queues_and_nodes(self):
        """Initialize queues and service nodes."""
        node_index = 0

        for queue_id in range(self.config.num_queues):
            # Create service nodes for this queue
            num_nodes = self.config.nodes_per_queue[queue_id]
            queue_nodes = []

            for i in range(num_nodes):
                service_rate = (
                    self.config.service_rates[node_index]
                    if node_index < len(self.config.service_rates)
                    else 3.0
                )
                node = ServiceNode(f"q{queue_id}_n{i}", service_rate)
                queue_nodes.append(node)
                self.service_nodes.append(node)
                node_index += 1

            # Create queue for these nodes
            queue = CarQueue(
                waitline=self.waitline,
                arrival_rate=0.0,  # We'll handle arrivals centrally
                service_rate=0.0,  # Service handled by individual nodes
                max_queue_length=self.config.max_queue_length,
                safe_distance=self.config.safe_distance,
            )

            # Override queue's service handling
            queue.service_nodes = queue_nodes
            queue.serving_car = None  # Will track per node

            self.queues.append(queue)

    def add_car(self, sampling_rate=10, phone_config=None):
        """
        Add a new car and assign it to a queue.

        Returns:
            tuple: (Car, queue_index) or (None, None) if no queue available
        """
        # Find available queue based on assignment strategy
        queue_index = self._assign_queue()

        if queue_index is None:
            return None, None

        # Add car to assigned queue
        car = self.queues[queue_index].add_car(sampling_rate, phone_config)
        if car:
            self.total_arrivals += 1
            car.queue_id = queue_index

        return car, queue_index

    def _assign_queue(self):
        """
        Assign car to a queue based on strategy.

        Returns:
            int: Queue index, or None if no queues available
        """
        if self.config.queue_assignment == "random":
            return np.random.choice(self.config.num_queues)

        elif self.config.queue_assignment == "shortest":
            # Find queue with shortest length
            queue_lengths = [len(q.cars) for q in self.queues]
            min_length = min(queue_lengths)
            candidates = [
                i for i, length in enumerate(queue_lengths) if length == min_length
            ]
            return np.random.choice(candidates) if candidates else None

        elif self.config.queue_assignment == "round_robin":
            # Round-robin assignment
            queue_index = self.next_queue_index
            self.next_queue_index = (self.next_queue_index + 1) % self.config.num_queues
            return queue_index

        else:
            return 0  # Default to first queue

    def advance_time(self, dt):
        """
        Advance simulation time and process all queues and service nodes.

        Args:
            dt: Time step (seconds)
        """
        self.current_time += dt

        # Process arrivals
        while self.current_time >= self.next_arrival_time:
            self.add_car()
            # Schedule next arrival with time-varying rate
            hour_of_day = (self.current_time / 3600) % 24
            if 6 <= hour_of_day < 9:  # morning rush
                current_rate = self.config.arrival_rate * 0.75
            elif 16 <= hour_of_day < 19:  # evening rush
                current_rate = self.config.arrival_rate * 0.9
            elif 22 <= hour_of_day or hour_of_day < 4:  # night
                current_rate = self.config.arrival_rate * 0.1
            else:  # off-peak
                current_rate = self.config.arrival_rate * 0.25

            if current_rate > 0:
                interarrival_minutes = np.random.exponential(1.0 / current_rate)
            else:
                interarrival_minutes = 60.0  # Fallback
            self.next_arrival_time += interarrival_minutes * 60

        # Update each queue's car positions
        for queue in self.queues:
            queue.advance_time(dt)

            # Try to start service for waiting cars
            self._process_queue_service(queue)

        # Process service completions
        completed_cars = []
        for node in self.service_nodes:
            if (
                node.is_busy
                and node.service_completion_time
                and self.current_time >= node.service_completion_time
            ):
                completed_car = node.complete_service(self.current_time)
                if completed_car:
                    completed_cars.append(completed_car)
                    self.total_completions += 1

        return completed_cars

    def _process_queue_service(self, queue):
        """
        Process service assignment for a queue.

        Args:
            queue: CarQueue to process
        """
        if not queue.car_positions:
            return

        # Find available service nodes for this queue
        available_nodes = [node for node in queue.service_nodes if node.is_available()]

        if not available_nodes:
            return  # No available nodes

        # Get first car in queue
        first_car_id = queue.car_positions[0]
        first_car = queue.cars[first_car_id]

        # Try to assign to an available node
        for node in available_nodes:
            if node.start_service(first_car, self.current_time):
                # Remove car from queue
                queue.car_positions.remove(first_car_id)
                break

    def get_statistics(self):
        """
        Get comprehensive border crossing statistics.

        Returns:
            BorderCrossingStats: Statistics as Pydantic model
        """
        queue_stats = []
        for i, queue in enumerate(self.queues):
            q_stats = queue.get_queue_statistics(i)
            queue_stats.append(q_stats)

        node_stats = []
        for i, queue in enumerate(self.queues):
            for node in queue.service_nodes:
                n_state = node.get_state(i)
                node_stats.append(
                    ServiceNodeStats(
                        node_id=n_state.node_id,
                        queue_id=n_state.queue_id,
                        service_rate=n_state.service_rate,
                        total_served=n_state.total_served,
                        total_service_time=n_state.total_service_time,
                        utilization=n_state.utilization,
                        average_service_time=(
                            n_state.total_service_time / n_state.total_served
                            if n_state.total_served > 0
                            else 0.0
                        ),
                    )
                )

        return (
            BorderCrossingStats(
                total_arrivals=self.total_arrivals,
                total_completions=self.total_completions,
                current_time=self.current_time,
                num_queues=self.config.num_queues,
                total_service_nodes=len(self.service_nodes),
                queue_assignment_strategy=self.config.queue_assignment,
                overall_utilization=self._calculate_overall_utilization(),
                throughput=(
                    self.total_completions / (self.current_time / 60)
                    if self.current_time > 0
                    else 0.0
                ),
            ),
            queue_stats,
            node_stats,
        )

    def _calculate_overall_utilization(self):
        """Calculate overall system utilization."""
        total_busy_nodes = sum(1 for node in self.service_nodes if node.is_busy)
        return total_busy_nodes / len(self.service_nodes) if self.service_nodes else 0.0

    def __repr__(self):
        return (
            f"BorderCrossing(queues={self.config.num_queues}, "
            f"nodes={len(self.service_nodes)}, "
            f"arrivals={self.total_arrivals})"
        )
