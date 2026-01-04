# Car Behavior Refactor Plan

## Overview
Simplify car behavior to be more realistic and traffic-like, where cars only respond to physical obstacles (other cars) rather than abstract queue states.

---

## Current Behavior (Problems)
- ❌ Cars check other cars' states (queued/serving/approaching)
- ❌ Complex logic for when to transition to "queued" state
- ❌ Artificial "queue zones" based on distance to booth
- ❌ Cars can queue far from booth if another car is queued

---

## New Behavior (Goals)

### 1. **Approaching State** (Default)
- ✅ Car follows its assigned path
- ✅ Car drives at preferred speed
- ✅ Car only cares about obstacles (other cars physically in the way)
- ✅ State remains "approaching" until physically blocked

### 2. **Queue Detection (Transition to "queued")**
- ✅ Trigger: Car detects another car directly in front
- ✅ Behavior:
  - Speed decreases to 0
  - Maintains safe distance from car ahead
  - **State changes to "queued"**
  - **Records `queue_start_time` (first time entering queued state)**
- ✅ No consideration of:
  - Other car's state
  - Distance to booth
  - "Queue zones"

### 3. **Queued State Behavior**
- ✅ Speed: 0 or slow crawl to maintain safe distance
- ✅ Movement trigger: Car ahead moves forward > safe distance
- ✅ Follow the leader: Match speed of car ahead (if any)
- ✅ Remains "queued" until reaching open booth

### 4. **Serving State (Transition)**
- ✅ Trigger: Car reaches an **open booth** (booth is available)
- ✅ Behavior:
  - State changes to "serving"
  - **Records `service_start_time`**
  - Speed = 0 (stopped at booth)
  - Booth processes the car

### 5. **Wait Time Tracking**
- ✅ Track per car:
  - `queue_start_time`: First moment car entered "queued" state
  - `service_start_time`: Moment car reached "serving" state
  - `wait_time = service_start_time - queue_start_time`
- ✅ Update running average:
  - Add each car's `wait_time` to total
  - Calculate: `average_wait_time = total_wait_time / num_cars_served`

---

## Implementation Tasks

### Task 1: Simplify Queue State Transition Logic
**File**: `cascabel/models/queue.py`
**Location**: `update_positions()` method, lines ~244-300

**Status**: ✅ COMPLETED

**Changes**:
- [x] Remove complex queue detection logic
- [x] Replace with simple car-following logic:
  ```python
  if car.status == "approaching":
      # Check if there's a car directly ahead
      car_ahead = find_car_ahead(car, sorted_cars)

      if car_ahead is not None:
          distance_to_ahead = car_ahead.position - car.position - car_ahead.length

          if distance_to_ahead < self.safe_distance * 2:
              # Transition to queued - first time blocked by traffic
              if car.status != "queued":
                  car.set_status("queued", current_time)
                  car.queue_start_time = current_time  # Track when queuing started

              # Stop or slow to maintain safe distance
              if distance_to_ahead < self.safe_distance:
                  target_velocity = 0
              else:
                  target_velocity = min(car.queue_velocity, car_ahead.velocity)
          else:
              # No obstruction - drive normally
              target_velocity = car.preferred_speed
      else:
          # No car ahead - drive normally
          target_velocity = car.preferred_speed
  ```

### Task 2: Update Queued State Logic
**File**: `cascabel/models/queue.py`
**Location**: Lines ~309-350

**Status**: ✅ COMPLETED

**Changes**:
- [x] Simplify queued car behavior
- [x] Remove complex spacing calculations
- [x] Focus on: "follow the car ahead at safe distance"
- [x] Cars remain in "queued" state once blocked (realistic traffic jam)

### Task 3: Update Serving Transition
**File**: `cascabel/models/queue.py`
**Location**: `start_service()` or service node assignment

**Changes**:
- [ ] Only transition to "serving" when booth is available
- [ ] Record `service_start_time` at transition
- [ ] Ensure `queue_start_time` was set earlier

### Task 4: Add Wait Time Tracking
**File**: `cascabel/models/car.py`

**Status**: ✅ COMPLETED

**Changes**:
- [x] Add attribute: `queue_start_time: Optional[float] = None`
- [x] Add attribute: `wait_time: Optional[float] = None`
- [x] Update `set_status()` to automatically record:
  - When status → "queued": set `queue_start_time` if not already set (line 216-217)
  - When status → "serving": calculate and store `wait_time` (line 219-224)

### Task 5: Update Wait Time Statistics
**File**: `cascabel/models/border_crossing.py` or queue stats

**Changes**:
- [ ] Track running sum of wait times
- [ ] Track count of cars served
- [ ] Calculate: `average_wait_time = total_wait / count`
- [ ] Expose via API/WebSocket

---

## Testing Checklist
- [ ] Car transitions to "queued" when blocked by car ahead
- [ ] Car transitions to "serving" when reaching open booth
- [ ] `queue_start_time` is recorded on first queue entry
- [ ] `service_start_time` is recorded when serving starts
- [ ] Wait time calculated correctly for each car
- [ ] Average wait time updates correctly
- [ ] Cars don't queue prematurely (far from booth)
- [ ] Cars move smoothly in traffic-like manner

---

## Benefits of New Approach
✅ **Simpler logic**: No complex state-based rules
✅ **More realistic**: Like real traffic (cars respond to obstacles)
✅ **Better metrics**: Accurate wait time from when traffic stopped
✅ **Easier to debug**: Clear cause-and-effect behavior
✅ **Natural queue formation**: Queue forms organically where traffic slows

---

## Questions to Resolve
- [ ] Should cars transition back to "approaching" if obstruction clears?
- [ ] How to handle lane switching with this model?
- [ ] Should "queued" vs "approaching" affect telemetry differently?
- [ ] What happens if a car is in "queued" state but then the car ahead leaves?

---

## Status
- [x] Plan created
- [x] Implementation started
- [x] Core logic implemented (Tasks 1-4)
- [ ] WebSocket integration
- [ ] Testing in progress
- [ ] Complete and verified

---

**Last Updated**: 2026-01-04
**Status**: Implementation Phase - Core Complete
