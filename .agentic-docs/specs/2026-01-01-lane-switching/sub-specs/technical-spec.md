# Technical Specification

This is the technical specification for the spec detailed in @.agentic-docs/specs/2026-01-01-lane-switching/spec.md

## Technical Requirements

### Lane Observation System

**Car Extension:**
- Add `observation_interval` (float, default: 5.0 seconds) - How often to check other queues
- Add `last_observation_time` (float) - Timestamp of last queue assessment
- Add `switching` (bool) - Flag indicating if currently switching lanes
- Add `target_queue_id` (int, nullable) - Queue being switched to
- Add `switch_start_time` (float, nullable) - When switch began

**Observation Logic:**
```python
def should_observe(current_time: float) -> bool:
    return current_time - last_observation_time >= observation_interval

def observe_queues(border_crossing: BorderCrossing) -> List[QueueObservation]:
    # Get neighboring queues (adjacent queue IDs)
    # Calculate estimated wait time for each queue:
    #   - Current queue length * average service time
    #   - Factor in service rate differences
    # Return sorted list by estimated wait time
```

### Decision Making Model

**Switching Decision:**
- **Threshold**: Only consider switching if neighbor queue wait time is >= X% shorter (default: 25%)
- **Probability**: Base probability of switching given threshold met (default: 0.7)
- **Cooldown**: Can't switch again for Y seconds after completing a switch (default: 30s)

**Decision Algorithm:**
```python
def decide_to_switch(observations: List[QueueObservation]) -> Optional[int]:
    current_wait = self.estimate_current_wait_time()
    best_queue = observations[0]

    # Check threshold
    if (current_wait - best_queue.wait_time) / current_wait < THRESHOLD:
        return None

    # Check cooldown
    if current_time - last_switch_time < COOLDOWN:
        return None

    # Probabilistic decision
    if random.random() < SWITCH_PROBABILITY:
        return best_queue.queue_id
    return None
```

### Lane Change Physics

**Lateral Movement:**
- **Duration**: Lane change takes 3-5 seconds (configurable)
- **Lateral Speed**: 2 m/s perpendicular to forward motion
- **Trajectory**: Linear interpolation from current queue position to target queue position
- **Forward Progress**: Car continues moving forward during switch (reduced velocity)

**Position Update:**
```python
def update_lane_switch(dt: float):
    if not self.switching:
        return

    progress = (current_time - switch_start_time) / SWITCH_DURATION

    if progress >= 1.0:
        # Complete switch
        self.position = target_queue_position
        self.queue_id = target_queue_id
        self.switching = False
    else:
        # Interpolate position
        self.position = lerp(start_pos, target_pos, progress)
        self.velocity *= 0.7  # Reduced forward speed during switch
```

### Enhanced Gyroscope Data

**Rotation During Switch:**
- **Yaw Change**: ±15-30 degrees depending on lane geometry
- **Roll**: ±2-5 degrees (vehicle body lean during lateral movement)
- **Pitch**: Minimal change (±1 degree)

**Telemetry Generation:**
```python
def generate_switch_telemetry():
    # Calculate rotation rate based on yaw change over switch duration
    yaw_rate = YAW_CHANGE / SWITCH_DURATION

    # Generate enhanced gyroscope data
    gyro_data = {
        'x': 0.0,  # pitch rate (minimal)
        'y': yaw_rate,  # yaw rate (significant)
        'z': ROLL_CHANGE / SWITCH_DURATION,  # roll rate
    }

    # Update quaternions to reflect rotation
    update_quaternions(yaw_delta, roll_delta)
```

### Queue Reassignment

**Safe Reassignment:**
1. **Check Target Queue**: Ensure target queue exists and has capacity
2. **Remove from Current**: Remove car from current queue's waitline
3. **Add to Target**: Insert car at appropriate position in target queue
4. **Update References**: Update car's queue_id, position, velocity
5. **Statistics**: Track switch count, success rate

**Border Crossing Integration:**
```python
def handle_lane_switch(car: Car, target_queue_id: int):
    current_queue = self.queues[car.queue_id]
    target_queue = self.queues[target_queue_id]

    # Remove from current
    current_queue.remove_car(car)

    # Calculate insertion point in target queue
    insertion_point = target_queue.find_insertion_point(car.position)

    # Add to target
    target_queue.insert_car(car, insertion_point)

    # Update car
    car.queue_id = target_queue_id
    car.last_switch_time = current_time

    # Statistics
    self.stats['lane_switches'] += 1
```

### Configuration Model

**New Configuration:**
```python
class LaneSwitchingConfig(BaseModel):
    enabled: bool = True
    observation_interval: float = 5.0  # seconds
    switch_threshold: float = 0.25  # 25% improvement required
    switch_probability: float = 0.7  # 70% chance if threshold met
    switch_duration: float = 4.0  # seconds to complete switch
    switch_cooldown: float = 30.0  # seconds before can switch again
    lateral_speed: float = 2.0  # m/s
```

**Integration with BorderCrossingConfig:**
```python
class BorderCrossingConfig(BaseModel):
    # ... existing fields ...
    lane_switching: Optional[LaneSwitchingConfig] = None
```

### API Updates

**Modified Endpoints:**
- `POST /simulate` - Accept `lane_switching` in configuration
- `GET /simulation/{id}/state` - Include lane switching statistics
  - `total_switches`: int
  - `switches_by_car`: Dict[str, int]
  - `average_switches_per_car`: float

### Performance Considerations

- Observation should be staggered across cars (not all observe simultaneously)
- Queue length calculation should be cached and updated incrementally
- Switch decision is O(1) operation (pre-sorted queue observations)
- Lateral movement doesn't require collision detection (simplified physics)

### Visualization Updates

**Frontend Changes:**
- RealtimeMapView: Animate car lateral movement during switches
- Add visual indicator (color change or icon) for switching cars
- CarTelemetryDashboard: Display switch count and current action
- QueueVisualization: Show cars in-transition between queues

## External Dependencies

No new external dependencies required. Uses existing numpy, random, and FastAPI infrastructure.
