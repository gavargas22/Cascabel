import numpy as np
from shapely.geometry import Point
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
        safe_distance=3.0,  # 3 meters between cars in queue
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

        # Track current time even when mm1_queue is None
        self._current_time = 0.0

        # Car management
        self.cars = {}  # car_id -> Car object
        self.car_positions = []  # Ordered list of car positions along queue
        self.next_car_id = 1

        # Queue state
        self.serving_car = None  # Car currently being served
        self.service_nodes = []  # Service nodes assigned to this queue

    def get_current_time(self):
        """Get current simulation time from mm1_queue or internal tracking."""
        if self.mm1_queue:
            return self.mm1_queue.current_time
        return self._current_time

    def add_car(self, car_id=None, sampling_rate=10, phone_config=None, car_waitline=None):
        """
        Add a new car to the queue.

        Args:
            car_id: Unique ID for the car (if None, uses internal counter)
            sampling_rate: Telemetry sampling rate
            phone_config: Phone configuration for telemetry
            car_waitline: Optional unique waitline for this car (for dynamic paths)

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

        # Use car-specific waitline if provided, otherwise use queue's shared waitline
        waitline_for_car = car_waitline if car_waitline is not None else self.waitline

        car = Car(car_id, sampling_rate, phone_config, initial_position=initial_position, waitline=waitline_for_car)

        # Set initial status to approaching and record arrival time
        current_time = self.get_current_time()
        car.set_status("approaching", current_time)

        # Give each car a preferred speed - check for custom physics config
        if hasattr(self, 'physics_config') and self.physics_config:
            # Use custom speed range
            speed_range = self.physics_config.max_speed_mps - self.physics_config.min_speed_mps
            car.preferred_speed = self.physics_config.min_speed_mps + (np.random.random() * speed_range)
            car.max_velocity = car.preferred_speed
            car.max_acceleration = self.physics_config.max_acceleration
            car.max_deceleration = -self.physics_config.max_deceleration
        else:
            # Default: 27-33 mph range (10% variance)
            speed_variance = np.random.uniform(0.9, 1.1)
            car.preferred_speed = car.max_velocity * speed_variance

        car.velocity = car.preferred_speed  # Start at preferred speed

        self.cars[car_id] = car

        # Initialize telemetry generator if phone config provided
        if phone_config:
            # Car will use its own waitline (either custom or shared)
            car.set_telemetry_generator()

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
            current_time = self.get_current_time()
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

    def get_car_coordinates(self, car):
        """
        Get the UTM coordinates of a car at its current position.

        Args:
            car: Car object

        Returns:
            tuple: (x_utm, y_utm) in meters or None if unavailable
        """
        if not hasattr(car, 'waitline') or car.waitline is None:
            return None

        try:
            # Get point on path at current position (lat/lon)
            point = car.waitline.interpolate(car.position)
            if point and hasattr(point, 'x') and hasattr(point, 'y'):
                # Convert to UTM using the waitline's projector
                if hasattr(car.waitline, 'projector'):
                    x_utm, y_utm = car.waitline.projector(point.x, point.y)
                    return (x_utm, y_utm)
                else:
                    # Fallback to lat/lon if no projector
                    return (point.x, point.y)
        except Exception:
            pass

        return None

    def calculate_geographic_distance(self, car1, car2):
        """
        Calculate the distance between two cars in meters using UTM coordinates.

        Args:
            car1: First car
            car2: Second car

        Returns:
            float: Distance in meters, or None if coordinates unavailable
        """
        coords1 = self.get_car_coordinates(car1)
        coords2 = self.get_car_coordinates(car2)

        if coords1 is None or coords2 is None:
            return None

        # Calculate Euclidean distance in UTM (already in meters)
        x_diff = coords2[0] - coords1[0]
        y_diff = coords2[1] - coords1[1]

        distance = np.sqrt(x_diff ** 2 + y_diff ** 2)

        return distance

    def get_booth_coordinates(self, car_waitline):
        """
        Get the booth coordinates in UTM from a car's waitline.

        Args:
            car_waitline: Car's waitline object

        Returns:
            tuple: (x_utm, y_utm) of booth in meters, or None if unavailable
        """
        if not car_waitline or not hasattr(car_waitline, 'end_point'):
            return None

        try:
            end_point = car_waitline.end_point
            if isinstance(end_point, (list, tuple)) and len(end_point) == 2:
                # end_point is in lat/lon, convert to UTM
                if hasattr(car_waitline, 'projector'):
                    x_utm, y_utm = car_waitline.projector(end_point[0], end_point[1])
                    return (x_utm, y_utm)
                else:
                    # Fallback to lat/lon
                    return tuple(end_point)
        except Exception:
            pass

        return None

    def calculate_distance_to_booth(self, car):
        """
        Calculate the distance from a car to the booth in meters using UTM.

        Args:
            car: Car object

        Returns:
            float: Distance in meters, or None if unavailable
        """
        car_coords = self.get_car_coordinates(car)
        if car_coords is None:
            return None

        car_waitline = car.waitline if hasattr(car, 'waitline') and car.waitline else self.waitline
        booth_coords = self.get_booth_coordinates(car_waitline)

        if booth_coords is None:
            return None

        # Calculate Euclidean distance in UTM (already in meters)
        x_diff = booth_coords[0] - car_coords[0]
        y_diff = booth_coords[1] - car_coords[1]

        distance = np.sqrt(x_diff ** 2 + y_diff ** 2)

        return distance

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

        # Get current simulation time for statistics
        current_time = self.get_current_time()

        # Debug: Print car state summary every 100 updates
        if not hasattr(self, '_update_count'):
            self._update_count = 0
        self._update_count += 1

        if self._update_count % 100 == 0:
            states = {}
            for car in self.cars.values():
                states[car.status] = states.get(car.status, 0) + 1
            print(f"\n=== Update {self._update_count} | Cars: {states} ===")

            # Test geographic distance calculation for first car
            if len(self.cars) > 0:
                test_car = list(self.cars.values())[0]
                coords = self.get_car_coordinates(test_car)
                dist_to_booth = self.calculate_distance_to_booth(test_car)

                coords_str = f"{coords[0]:.1f},{coords[1]:.1f}" if coords else 'FAIL'
                dist_str = f"{dist_to_booth:.1f}m" if dist_to_booth is not None else 'FAIL'

                print(f"TEST Car {test_car.car_id}: coords={coords_str}, dist_to_booth={dist_str}")

                # Debug why it's failing
                if coords is None:
                    print(f"  → coords FAILED: waitline={test_car.waitline is not None}, "
                          f"position={test_car.position:.1f}")
                    if test_car.waitline:
                        try:
                            point = test_car.waitline.interpolate(test_car.position)
                            print(f"  → interpolate returned: {point}")
                            if point:
                                print(f"  → point.x={point.x}, point.y={point.y}")
                                print(f"  → has projector: {hasattr(test_car.waitline, 'projector')}")
                        except Exception as e:
                            print(f"  → interpolate ERROR: {e}")

        # Sort cars by position (front of queue first - HIGHEST position number)
        # Position increases as cars approach the booth (toward waitline_length)
        # Only sort by position - cars that arrive first physically will naturally be ahead
        sorted_cars = sorted(self.cars.values(), key=lambda c: -c.position)

        # Get traffic control points from shared waitline (for cars without their own)
        shared_traffic_control_points = self.waitline.traffic_control_points if self.waitline else []
        shared_booth_position = self.waitline.waitline_length if self.waitline else 1000.0

        # Find booth position from shared traffic control points
        if shared_traffic_control_points:
            for cp in shared_traffic_control_points:
                if cp['type'] == 'booth':
                    shared_booth_position = cp['position_meters']
                    break

        # Update each car's target velocity based on position in queue
        for i, car in enumerate(sorted_cars):
            # Get car-specific path info (use car's own waitline if available)
            car_waitline = car.waitline if hasattr(car, 'waitline') and car.waitline else self.waitline
            car_traffic_control_points = (
                car_waitline.traffic_control_points if car_waitline and hasattr(car_waitline, 'traffic_control_points')
                else shared_traffic_control_points
            )
            car_path_length = car_waitline.waitline_length if car_waitline else shared_booth_position

            # Find booth position for this specific car
            booth_position = car_path_length
            if car_traffic_control_points:
                for cp in car_traffic_control_points:
                    if cp['type'] == 'booth':
                        booth_position = cp['position_meters']
                        break

            # Assign each car a preferred speed with variance (27-33 mph range)
            if not hasattr(car, 'preferred_speed'):
                speed_variance = np.random.uniform(0.9, 1.1)
                car.preferred_speed = car.max_velocity * speed_variance

            # Handle approaching cars (moving toward booth)
            if car.status == "approaching":
                # Use geographic distance to booth instead of path position
                geo_distance_to_booth = self.calculate_distance_to_booth(car)
                if geo_distance_to_booth is None:
                    # Fallback to path-based distance if geographic distance unavailable
                    geo_distance_to_booth = booth_position - car.position

                # Find the closest car geographically (regardless of distance to booth)
                # This prevents piling up when multiple cars are near booth
                car_ahead = None
                min_distance = float('inf')
                detection_range = 50.0  # Check cars within 50m for early detection

                # Check ALL cars in ALL queues for collision (not just sorted_cars)
                all_cars = list(self.cars.values())
                for other_car in all_cars:
                    if other_car.car_id == car.car_id:
                        continue

                    # Calculate GEOGRAPHIC distance between cars
                    geographic_distance = self.calculate_geographic_distance(car, other_car)

                    if geographic_distance is not None and geographic_distance < detection_range:
                        # Get other car's distance to booth
                        other_geo_distance_to_booth = self.calculate_distance_to_booth(other_car)
                        if other_geo_distance_to_booth is None:
                            continue

                        # Consider car as "ahead" if it's closer to booth OR very close geographically
                        # This handles converging paths where cars might be side by side
                        is_ahead = (other_geo_distance_to_booth < geo_distance_to_booth) or (geographic_distance < self.safe_distance * 3)

                        if is_ahead:
                            # Subtract other car's length to get gap
                            distance_between = geographic_distance - other_car.length

                            # Find the closest car
                            if abs(distance_between) < abs(min_distance):
                                min_distance = distance_between
                                car_ahead = other_car

                # Get traffic control speed limit
                control_speed_limit = self.get_control_point_speed_limit(
                    car.position, car_traffic_control_points, car.preferred_speed
                )

                # CRITICAL: Only transition to queued when NEAR BOOTH and BLOCKED
                # Check if we should transition to queued state (using geographic distance)
                should_transition_to_queued = False

                # Also check path-based distance (car near end of path)
                car_waitline = car.waitline if hasattr(car, 'waitline') and car.waitline else self.waitline
                path_distance_to_end = 0
                if car_waitline and hasattr(car_waitline, 'waitline_length'):
                    path_distance_to_end = car_waitline.waitline_length - car.position

                # Use either geographic distance OR path distance (whichever indicates closer to booth)
                effective_distance_to_booth = min(geo_distance_to_booth, path_distance_to_end) if path_distance_to_end > 0 else geo_distance_to_booth

                if effective_distance_to_booth < 100:  # Must be in booth area (100m)
                    if car_ahead is not None and min_distance < self.safe_distance * 1.5:
                        # Blocked by car ahead in booth area - this is a queue
                        should_transition_to_queued = True
                    elif effective_distance_to_booth < 5 and car_ahead is None:
                        # Reached booth with no car ahead - about to be served
                        should_transition_to_queued = True
                    elif path_distance_to_end < 3:
                        # Car is at end of path - must transition
                        should_transition_to_queued = True

                if should_transition_to_queued:
                    current_time = self.get_current_time()
                    car.set_status("queued", current_time)
                    if car.car_id <= 10:
                        print(f">>> Car {car.car_id} ENTERED QUEUED state at geo={geo_distance_to_booth:.1f}m, path_end={path_distance_to_end:.1f}m")
                    # Will handle movement in queued state below
                else:
                    # Still approaching - handle car following and booth approach
                    # Detect cars from further away to prevent piling up
                    if car_ahead is not None:
                        # Car ahead detected - maintain safe distance
                        if min_distance <= 0:
                            # Overlapping! Stop immediately
                            target_velocity = 0.0
                        elif min_distance < self.safe_distance:
                            # Too close - STOP completely
                            target_velocity = 0.0
                        elif min_distance < self.safe_distance * 2:
                            # Very close - slow crawl (don't depend on car_ahead velocity)
                            target_velocity = car.queue_velocity * 0.3
                        elif min_distance < self.safe_distance * 3:
                            # Close - slow down significantly
                            target_velocity = car.queue_velocity * 0.5
                        elif min_distance < self.safe_distance * 5:
                            # Moderate distance - accelerate to close gap
                            target_velocity = control_speed_limit * 0.6
                        elif min_distance < self.safe_distance * 8:
                            # Approaching car ahead - drive normally
                            target_velocity = control_speed_limit * 0.8
                        else:
                            # Far enough - normal driving
                            target_velocity = control_speed_limit * 0.9
                    else:
                        # No car ahead - normal driving
                        if geo_distance_to_booth < 50:
                            # Approaching booth - slow down
                            slowdown_factor = geo_distance_to_booth / 50.0
                            target_velocity = max(car.queue_velocity, control_speed_limit * slowdown_factor)
                        elif geo_distance_to_booth < 5:
                            # Very close to booth - stop
                            target_velocity = 0.0
                        else:
                            target_velocity = control_speed_limit

                    car.update_physics(target_velocity, dt)
                    car.update_statistics(current_time, dt)

            elif car.status == "serving":
                # Car being served - stationary at booth
                target_velocity = 0.0
                car.position = booth_position  # Keep at booth
                car.update_physics(target_velocity, dt)
                car.update_statistics(current_time, dt)

            elif car.status == "queued":
                # GAME-LIKE APPROACH: Simple collision detection
                # Check ALL other cars, find closest one that's blocking

                geo_distance_to_booth = self.calculate_distance_to_booth(car)
                if geo_distance_to_booth is None:
                    geo_distance_to_booth = booth_position - car.position

                # Find the closest blocking car (game-like collision detection)
                car_ahead = None
                min_distance = float('inf')
                detection_range = 30.0  # meters - wider range for queued cars

                for other_car in self.cars.values():
                    if other_car.car_id == car.car_id:
                        continue

                    # Calculate geographic distance
                    geo_dist = self.calculate_geographic_distance(car, other_car)
                    if geo_dist is None or geo_dist > detection_range:
                        continue  # Too far away

                    # Calculate other car's distance to booth
                    other_dist_to_booth = self.calculate_distance_to_booth(other_car)
                    if other_dist_to_booth is None:
                        continue

                    # Car is "blocking" if it's closer to booth OR very close geographically
                    is_blocking = (other_dist_to_booth < geo_distance_to_booth) or (geo_dist < self.safe_distance * 3)

                    if is_blocking:
                        # This car is ahead - calculate actual gap
                        gap = geo_dist - other_car.length

                        # Is this the closest blocking car?
                        if gap < min_distance:
                            min_distance = gap
                            car_ahead = other_car

                # Debug logging - print for ALL queued cars
                if car.car_id <= 10:  # First 10 cars
                    gap_str = f"{min_distance:.1f}m" if car_ahead and min_distance != float('inf') else 'N/A'
                    print(f"[QUEUED] Car {car.car_id}: booth_dist={geo_distance_to_booth:.1f}m, "
                          f"car_ahead={car_ahead.car_id if car_ahead else 'NONE'}, "
                          f"gap={gap_str}, vel={car.velocity:.2f}m/s")

                if car_ahead is None:
                    # No car ahead - move toward booth (use geographic distance)
                    # CRITICAL: Only approach if distance > safe_distance
                    if geo_distance_to_booth > self.safe_distance * 2:
                        target_velocity = car.queue_velocity
                    elif geo_distance_to_booth > self.safe_distance:
                        # Approaching booth - slow down
                        target_velocity = car.queue_velocity * 0.5
                    elif geo_distance_to_booth > 1.0:
                        # Very close - slow crawl to booth
                        target_velocity = car.queue_velocity * 0.2
                    else:
                        # At booth - complete stop and wait for service
                        target_velocity = 0.0
                        # Snap to booth position to prevent drift
                        car.position = min(car.position, booth_position)
                else:
                    # Follow car ahead - maintain safe distance
                    # CRITICAL: Stop if ANY car is ahead and within safe distance
                    if min_distance <= 0:
                        # Overlapping! Stop immediately and don't move
                        target_velocity = 0.0
                    elif min_distance < self.safe_distance:
                        # Too close - STOP completely
                        target_velocity = 0.0
                    elif min_distance < self.safe_distance * 1.5:
                        # Approaching safe distance - very slow crawl
                        target_velocity = car.queue_velocity * 0.3
                    elif min_distance < self.safe_distance * 2:
                        # Good spacing - slow queue speed
                        target_velocity = car.queue_velocity * 0.6
                    elif min_distance < self.safe_distance * 3:
                        # Comfortable distance - normal queue speed
                        target_velocity = car.queue_velocity
                    else:
                        # Large gap - move forward to close gap
                        # Don't limit by car_ahead velocity - accelerate independently
                        # This allows cars to resume after the path clears
                        target_velocity = car.queue_velocity * 1.5

                car.update_physics(target_velocity, dt)
                car.update_statistics(current_time, dt)

            elif car.status == "completed":
                # Car has finished service, now driving away from booth
                # Use moderate exit speed to clear booth quickly but not excessively
                target_velocity = car.queue_velocity * 2.0  # 2x queue speed ≈ 6 mph
                car.update_physics(target_velocity, dt)
                car.update_statistics(current_time, dt)

        # Remove completed cars that have driven far enough past booth
        removal_distance = 5.0  # Remove cars 5m past booth (just enough to clear)
        cars_to_remove = []
        for car in self.cars.values():
            if car.status == "completed":
                # Check if car has driven far enough past booth to be removed
                if car.position > booth_position + removal_distance:
                    # Set exit time before removing
                    if not car.exit_time:
                        car.exit_time = current_time
                    cars_to_remove.append(car.car_id)

        # Remove cars that have exited (they remain in car_history for lookup)
        for car_id in cars_to_remove:
            if car_id in self.cars:
                del self.cars[car_id]
            if car_id in self.car_positions:
                self.car_positions.remove(car_id)

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
                current_time = self.get_current_time()
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
        # Always update internal time tracking
        self._current_time += dt

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
