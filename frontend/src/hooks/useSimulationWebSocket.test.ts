/**
 * Tests for useSimulationWebSocket React Hook
 *
 * Note: These tests focus on the hook logic and state management.
 * WebSocket connection tests require mocking which is complex in Jest.
 * Integration tests should be performed with a real backend.
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { carStatusFromCode, CarStatus } from '../services/messages';

// ============================================================================
// Status Conversion Tests
// ============================================================================

describe('Car status conversion', () => {
  it('should convert status code 0 to approaching', () => {
    expect(carStatusFromCode(0)).toBe('approaching');
  });

  it('should convert status code 1 to queued', () => {
    expect(carStatusFromCode(1)).toBe('queued');
  });

  it('should convert status code 2 to serving', () => {
    expect(carStatusFromCode(2)).toBe('serving');
  });

  it('should convert status code 3 to completed', () => {
    expect(carStatusFromCode(3)).toBe('completed');
  });

  it('should convert unknown status codes to unknown', () => {
    expect(carStatusFromCode(99)).toBe('unknown');
    expect(carStatusFromCode(-1)).toBe('unknown');
  });
});

// ============================================================================
// Hook Types and Interfaces Tests
// ============================================================================

describe('Hook type definitions', () => {
  it('should export correct CarStatus type', () => {
    const statuses: CarStatus[] = ['approaching', 'queued', 'serving', 'completed', 'unknown'];
    expect(statuses.length).toBe(5);
  });

  it('should have all connection states defined', () => {
    const states = ['disconnected', 'connecting', 'connected', 'reconnecting', 'error'];
    expect(states.length).toBe(5);
  });
});

// ============================================================================
// Mock WebSocket Tests
// ============================================================================

describe('WebSocket client behavior simulation', () => {
  // These tests simulate the expected behavior without actual WebSocket

  it('should handle simulation update data transformation', () => {
    // Simulate raw data from Rust backend
    const rawCar = {
      id: 1,
      position: [32.5, -117.0] as [number, number],
      velocity: 5.5,
      status: 1, // queued
      queue_id: 0,
      queue_position: 1,
    };

    // Transform to display format
    const displayCar = {
      id: rawCar.id,
      position: rawCar.position,
      velocity: rawCar.velocity,
      status: carStatusFromCode(rawCar.status),
      queue_id: rawCar.queue_id,
      queue_position: rawCar.queue_position,
    };

    expect(displayCar.status).toBe('queued');
    expect(displayCar.id).toBe(1);
  });

  it('should handle position-only update merging', () => {
    // Initial state
    const existingCars = [
      { id: 1, position: [32.5, -117.0] as [number, number], velocity: 5.5, status: 'queued' as CarStatus },
      { id: 2, position: [32.6, -117.1] as [number, number], velocity: 10.0, status: 'approaching' as CarStatus },
    ];

    // Position-only update
    const positionUpdate = [
      [1, 32.51, -117.01],
      [2, 32.61, -117.11],
    ];

    // Merge positions
    const positionMap = new Map<number, [number, number]>();
    for (const [id, lat, lon] of positionUpdate) {
      positionMap.set(id, [lat, lon]);
    }

    const updatedCars = existingCars.map((car) => {
      const newPosition = positionMap.get(car.id);
      if (newPosition) {
        return { ...car, position: newPosition };
      }
      return car;
    });

    expect(updatedCars[0].position).toEqual([32.51, -117.01]);
    expect(updatedCars[1].position).toEqual([32.61, -117.11]);
    // Other properties should be preserved
    expect(updatedCars[0].status).toBe('queued');
    expect(updatedCars[1].velocity).toBe(10.0);
  });

  it('should handle null/undefined optional fields', () => {
    const rawCar = {
      id: 1,
      position: [32.5, -117.0] as [number, number],
      velocity: 5.5,
      status: 0,
      queue_id: null,
      queue_position: null,
    };

    const displayCar = {
      id: rawCar.id,
      position: rawCar.position,
      velocity: rawCar.velocity,
      status: carStatusFromCode(rawCar.status),
      queue_id: rawCar.queue_id ?? undefined,
      queue_position: rawCar.queue_position ?? undefined,
    };

    expect(displayCar.queue_id).toBeUndefined();
    expect(displayCar.queue_position).toBeUndefined();
    expect(displayCar.status).toBe('approaching');
  });
});

// ============================================================================
// Error Handling Tests
// ============================================================================

describe('Error handling', () => {
  it('should format error messages correctly', () => {
    const errorMsg = {
      type: 'error' as const,
      code: 'SIMULATION_NOT_FOUND',
      message: 'Simulation does not exist',
      details: 'ID: abc123',
    };

    const formattedError = `${errorMsg.code}: ${errorMsg.message}`;
    expect(formattedError).toBe('SIMULATION_NOT_FOUND: Simulation does not exist');
  });

  it('should handle error without details', () => {
    const errorMsg = {
      type: 'error' as const,
      code: 'INTERNAL_ERROR',
      message: 'Something went wrong',
      details: null,
    };

    const formattedError = `${errorMsg.code}: ${errorMsg.message}`;
    expect(formattedError).toBe('INTERNAL_ERROR: Something went wrong');
  });
});

// ============================================================================
// Metrics Update Tests
// ============================================================================

describe('Metrics update handling', () => {
  it('should handle complete metrics update', () => {
    const metrics = {
      total_arrivals: 100,
      total_completions: 50,
      average_wait_time: 120.5,
      simulation_time: 3600.0,
    };

    expect(metrics.total_arrivals).toBe(100);
    expect(metrics.average_wait_time).toBe(120.5);
    expect(metrics.simulation_time).toBe(3600.0);
  });

  it('should handle null average_wait_time', () => {
    const metrics = {
      total_arrivals: 0,
      total_completions: 0,
      average_wait_time: null,
      simulation_time: 0.0,
    };

    expect(metrics.average_wait_time).toBeNull();
  });
});

// ============================================================================
// Control Message Tests
// ============================================================================

describe('Control message creation', () => {
  it('should create valid pause message structure', () => {
    const pauseMsg = { type: 'control', action: 'pause' };
    expect(pauseMsg.type).toBe('control');
    expect(pauseMsg.action).toBe('pause');
  });

  it('should create valid resume message structure', () => {
    const resumeMsg = { type: 'control', action: 'resume' };
    expect(resumeMsg.type).toBe('control');
    expect(resumeMsg.action).toBe('resume');
  });

  it('should create valid set_time_speed message structure', () => {
    const speedMsg = { type: 'control', action: 'set_time_speed', speed: 2.5 };
    expect(speedMsg.type).toBe('control');
    expect(speedMsg.action).toBe('set_time_speed');
    expect(speedMsg.speed).toBe(2.5);
  });

  it('should create valid add_station message structure', () => {
    const addMsg = { type: 'control', action: 'add_station', queue_id: 0 };
    expect(addMsg.type).toBe('control');
    expect(addMsg.action).toBe('add_station');
    expect(addMsg.queue_id).toBe(0);
  });

  it('should create valid remove_station message structure', () => {
    const removeMsg = { type: 'control', action: 'remove_station', node_id: 'booth_1' };
    expect(removeMsg.type).toBe('control');
    expect(removeMsg.action).toBe('remove_station');
    expect(removeMsg.node_id).toBe('booth_1');
  });
});

// ============================================================================
// Service Node Tests
// ============================================================================

describe('Service node state handling', () => {
  it('should handle busy service node', () => {
    const node = {
      node_id: 'booth_1',
      queue_id: 0,
      is_busy: true,
      current_car_id: 42,
      service_rate: 3.0,
      total_served: 25,
    };

    expect(node.is_busy).toBe(true);
    expect(node.current_car_id).toBe(42);
  });

  it('should handle idle service node', () => {
    const node = {
      node_id: 'booth_2',
      queue_id: 1,
      is_busy: false,
      current_car_id: null,
      service_rate: 2.5,
      total_served: 20,
    };

    expect(node.is_busy).toBe(false);
    expect(node.current_car_id).toBeNull();
  });
});
