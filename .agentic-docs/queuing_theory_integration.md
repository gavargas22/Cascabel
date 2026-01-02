# Queuing Theory Integration: M/M/1 Model for Car Queues

## Overview
Implement M/M/1 queuing theory to simulate realistic car arrival and service patterns in border bridge queues.

## M/M/1 Model Basics

### Model Parameters
- **λ (lambda)**: Arrival rate (cars per unit time)
- **μ (mu)**: Service rate (cars processed per unit time)
- **ρ (rho)**: Utilization factor = λ/μ (must be < 1 for stability)

### Key Metrics
- **Average queue length**: L = ρ/(1-ρ)
- **Average waiting time**: W = 1/(μ-λ)
- **Probability of n cars in system**: P(n) = (1-ρ) * ρ^n

## Implementation in Cascabel

### Car Arrival Process
```python
import numpy as np

class ArrivalProcess:
    def __init__(self, arrival_rate):
        self.arrival_rate = arrival_rate  # cars per minute

    def generate_interarrival_time(self):
        """Generate time until next car arrives (exponential distribution)"""
        return np.random.exponential(1.0 / self.arrival_rate)

    def generate_arrival_times(self, simulation_duration):
        """Generate list of arrival times over simulation period"""
        arrival_times = []
        current_time = 0.0

        while current_time < simulation_duration:
            interarrival = self.generate_interarrival_time()
            current_time += interarrival
            if current_time < simulation_duration:
                arrival_times.append(current_time)

        return arrival_times
```

### Service Process
```python
class ServiceProcess:
    def __init__(self, service_rate, service_time_variation=0.2):
        self.service_rate = service_rate  # cars per minute
        self.mean_service_time = 1.0 / service_rate
        self.service_time_variation = service_time_variation

    def generate_service_time(self):
        """Generate service time for a car (exponential distribution)"""
        return np.random.exponential(self.mean_service_time)

    def generate_variable_service_time(self):
        """Generate service time with variation"""
        base_time = self.generate_service_time()
        variation = np.random.normal(0, self.service_time_variation)
        return max(0.1, base_time + variation)  # minimum 6 seconds
```

### Queue Management
```python
class CarQueue:
    def __init__(self, arrival_process, service_process, max_length=50):
        self.arrival_process = arrival_process
        self.service_process = service_process
        self.max_length = max_length

        self.queue = []  # list of cars in queue
        self.arrival_times = []
        self.service_start_times = []
        self.departure_times = []

    def add_car(self, car, arrival_time):
        """Add car to queue if space available"""
        if len(self.queue) < self.max_length:
            self.queue.append(car)
            self.arrival_times.append(arrival_time)
            return True
        return False  # queue full

    def process_next_car(self, current_time):
        """Process next car in queue"""
        if not self.queue:
            return None

        car = self.queue.pop(0)
        arrival_time = self.arrival_times.pop(0)

        # Calculate waiting time
        waiting_time = current_time - arrival_time
        service_time = self.service_process.generate_service_time()

        self.service_start_times.append(current_time)
        departure_time = current_time + service_time
        self.departure_times.append(departure_time)

        return {
            'car': car,
            'arrival_time': arrival_time,
            'waiting_time': waiting_time,
            'service_time': service_time,
            'departure_time': departure_time
        }
```

## Integration with Simulation

### Enhanced Simulation Class
```python
class EnhancedSimulation:
    def __init__(self, waitline, arrival_rate, service_rate):
        self.waitline = waitline
        self.arrival_process = ArrivalProcess(arrival_rate)
        self.service_process = ServiceProcess(service_rate)
        self.car_queue = CarQueue(self.arrival_process, self.service_process)

        self.cars = []  # all cars in simulation
        self.active_cars = []  # cars currently moving
        self.completed_cars = []

        self.current_time = 0.0
        self.simulation_duration = 3600  # 1 hour

    def initialize_cars(self):
        """Generate initial car arrivals"""
        arrival_times = self.arrival_process.generate_arrival_times(
            self.simulation_duration
        )

        for i, arrival_time in enumerate(arrival_times):
            car = Car(car_id=f"car_{i}", arrival_time=arrival_time)
            self.cars.append(car)

            # Add to queue if possible
            if self.car_queue.add_car(car, arrival_time):
                car.status = "queued"
            else:
                car.status = "balked"  # couldn't join queue

    def run_simulation(self):
        """Main simulation loop"""
        self.initialize_cars()

        while self.current_time < self.simulation_duration:
            # Process car departures from service
            departure_info = self.car_queue.process_next_car(self.current_time)
            if departure_info:
                car = departure_info['car']
                car.status = "serving"
                car.service_start_time = departure_info['departure_time']
                self.active_cars.append(car)

            # Move active cars along waitline
            self.update_car_positions()

            # Advance time
            self.current_time += self.time_step

        self.finalize_results()

    def update_car_positions(self):
        """Update positions of cars currently being served"""
        for car in self.active_cars[:]:  # copy for safe iteration
            # Calculate position based on time since service start
            time_since_service = self.current_time - car.service_start_time
            position = self.calculate_position_along_waitline(time_since_service, car)

            if position >= self.waitline.total_length:
                # Car has completed crossing
                car.status = "completed"
                car.completion_time = self.current_time
                self.active_cars.remove(car)
                self.completed_cars.append(car)
            else:
                car.current_position = position
                # Generate telemetry data
                self.generate_telemetry(car)
```

## Realistic Parameters

### Border Bridge Queues
- **Arrival Rate (λ)**: 0.5 - 2.0 cars/minute (depends on time of day)
- **Service Rate (μ)**: 0.8 - 1.5 cars/minute (processing time 40-75 seconds)
- **Utilization (ρ)**: 0.4 - 0.8 (moderate to high congestion)

### Time-of-Day Variations
```python
def get_time_based_rates(hour):
    """Get arrival/service rates based on time of day"""
    if 6 <= hour < 9:  # morning rush
        return {"arrival": 1.5, "service": 1.0}
    elif 16 <= hour < 19:  # evening rush
        return {"arrival": 1.8, "service": 0.9}
    else:  # off-peak
        return {"arrival": 0.3, "service": 1.2}
```

## Validation

### Statistical Tests
- **Chi-square test**: Validate interarrival times follow exponential distribution
- **Queue length distribution**: Compare against theoretical M/M/1 predictions
- **Waiting time analysis**: Verify average waiting times match theory

### Performance Metrics
- **Average queue length**: Should match L = ρ/(1-ρ)
- **Average waiting time**: Should match W = 1/(μ-λ)
- **Server utilization**: Should approach ρ

## Extensions

### M/M/c Model (Multiple Servers)
For bridges with multiple lanes:
```python
class MultiServerQueue(CarQueue):
    def __init__(self, arrival_process, service_process, num_servers=2):
        super().__init__(arrival_process, service_process)
        self.num_servers = num_servers
        self.available_servers = num_servers
```

### Multi-Lane Queue Networks
Future implementation will support complex lane configurations:

```python
class MultiLaneQueueNetwork:
    def __init__(self, crossing_config):
        self.lanes = {}
        for lane_id, lane_config in crossing_config['lanes'].items():
            self.lanes[lane_id] = LaneQueue(
                arrival_rate=lane_config['arrival_rate'],
                service_rate=lane_config['service_rate'],
                capacity=lane_config['capacity']
            )

    def switch_lane(self, car, from_lane, to_lane):
        """Handle car switching between lanes"""
        if self.can_switch(car, from_lane, to_lane):
            self.lanes[from_lane].remove_car(car)
            self.lanes[to_lane].add_car(car)
            # Generate lane switch telemetry
            self.generate_lane_switch_telemetry(car, from_lane, to_lane)

    def can_switch(self, car, from_lane, to_lane):
        """Check if lane switch is safe and allowed"""
        # Check distance to next car
        # Check lane availability
        # Check crossing policies
        pass
```

### Lane Switching Queuing Theory
Lane switching introduces additional complexity:
- **Balking**: Cars may choose not to switch lanes if target lane is congested
- **Jockeying**: Cars switching lanes to find shorter queues
- **Merging**: Multiple lanes feeding into processing booths
- **Priority**: Some lanes (e.g., SENTRI) have priority processing

### Time-Varying Rates
Arrival/service rates that change over time to simulate rush hours, with lane-specific variations.