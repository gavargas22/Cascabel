/**
 * Tests for Binary WebSocket Client
 *
 * Tests cover:
 * - MessagePack decoding
 * - JSON fallback parsing
 * - Reconnection with exponential backoff
 * - Control message sending
 * - Connection state management
 * - Heartbeat mechanism
 */

import { encode, decode } from '@msgpack/msgpack';
import {
  ServerMessage,
  ClientMessage,
  SimulationUpdate,
  PositionOnlyUpdate,
  MetricsUpdate,
  CarState,
  parseServerMessage,
  createControlMessage,
  createHeartbeatMessage,
  createRequestFullStateMessage,
} from './messages';

// ============================================================================
// MessagePack Decoding Tests (7.1)
// ============================================================================

describe('MessagePack message decoding', () => {
  it('should decode a SimulationUpdate message from MessagePack binary', () => {
    const message = {
      type: 'simulation_update',
      cars: [
        {
          id: 1,
          position: [32.5, -117.0],
          velocity: 5.5,
          status: 1, // queued
          queue_id: 0,
          queue_position: 1,
        },
      ],
      metrics: {
        total_arrivals: 100,
        total_completions: 50,
        average_wait_time: 120.5,
        simulation_time: 3600.0,
      },
      service_nodes: [
        {
          node_id: 'booth_1',
          queue_id: 0,
          is_busy: true,
          current_car_id: 1,
          service_rate: 3.0,
          total_served: 50,
        },
      ],
      timestamp: 1234567890.123,
    };

    // Encode to MessagePack binary
    const encoded = encode(message);
    expect(encoded).toBeInstanceOf(Uint8Array);

    // Decode back
    const decoded = decode(encoded);
    expect(decoded).toEqual(message);

    // Parse into typed message
    const parsed = parseServerMessage(decoded);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('simulation_update');
    if (parsed?.type === 'simulation_update') {
      expect(parsed.cars.length).toBe(1);
      expect(parsed.cars[0].id).toBe(1);
      expect(parsed.metrics.total_arrivals).toBe(100);
    }
  });

  it('should decode a PositionOnlyUpdate message from MessagePack binary', () => {
    const message = {
      type: 'position_only',
      positions: [
        [1, 32.5, -117.0],
        [2, 32.6, -117.1],
        [3, 32.7, -117.2],
      ],
      timestamp: 1234567890.123,
    };

    const encoded = encode(message);
    const decoded = decode(encoded);
    const parsed = parseServerMessage(decoded);

    expect(parsed?.type).toBe('position_only');
    if (parsed?.type === 'position_only') {
      expect(parsed.positions.length).toBe(3);
      expect(parsed.positions[0]).toEqual([1, 32.5, -117.0]);
    }
  });

  it('should decode a Heartbeat message from MessagePack binary', () => {
    const message = { type: 'heartbeat' };

    const encoded = encode(message);
    const decoded = decode(encoded);
    const parsed = parseServerMessage(decoded);

    expect(parsed?.type).toBe('heartbeat');
  });

  it('should decode an Error message from MessagePack binary', () => {
    const message = {
      type: 'error',
      code: 'SIMULATION_NOT_FOUND',
      message: 'Simulation does not exist',
      details: 'ID: abc123',
    };

    const encoded = encode(message);
    const decoded = decode(encoded);
    const parsed = parseServerMessage(decoded);

    expect(parsed?.type).toBe('error');
    if (parsed?.type === 'error') {
      expect(parsed.code).toBe('SIMULATION_NOT_FOUND');
      expect(parsed.message).toBe('Simulation does not exist');
      expect(parsed.details).toBe('ID: abc123');
    }
  });

  it('should decode an Ack message from MessagePack binary', () => {
    const message = {
      type: 'ack',
      message_id: 'msg_123',
    };

    const encoded = encode(message);
    const decoded = decode(encoded);
    const parsed = parseServerMessage(decoded);

    expect(parsed?.type).toBe('ack');
    if (parsed?.type === 'ack') {
      expect(parsed.message_id).toBe('msg_123');
    }
  });

  it('should handle MessagePack with null optional fields', () => {
    const message = {
      type: 'simulation_update',
      cars: [
        {
          id: 1,
          position: [32.5, -117.0],
          velocity: 5.5,
          status: 0, // approaching
          queue_id: null,
          queue_position: null,
        },
      ],
      metrics: {
        total_arrivals: 10,
        total_completions: 5,
        average_wait_time: null,
        simulation_time: 300.0,
      },
      service_nodes: [],
      timestamp: 1234567890.123,
    };

    const encoded = encode(message);
    const decoded = decode(encoded);
    const parsed = parseServerMessage(decoded);

    expect(parsed?.type).toBe('simulation_update');
    if (parsed?.type === 'simulation_update') {
      expect(parsed.cars[0].queue_id).toBeNull();
      expect(parsed.metrics.average_wait_time).toBeNull();
    }
  });

  it('should return null for invalid message format', () => {
    expect(parseServerMessage(null)).toBeNull();
    expect(parseServerMessage(undefined)).toBeNull();
    expect(parseServerMessage('string')).toBeNull();
    expect(parseServerMessage(123)).toBeNull();
    expect(parseServerMessage({})).toBeNull();
    expect(parseServerMessage({ notType: 'foo' })).toBeNull();
  });

  it('should return null for unknown message type', () => {
    const message = { type: 'unknown_type', data: {} };
    const parsed = parseServerMessage(message);
    expect(parsed).toBeNull();
  });
});

// ============================================================================
// SimulationUpdate Message Parsing Tests (7.4)
// ============================================================================

describe('SimulationUpdate message parsing', () => {
  it('should parse a complete SimulationUpdate with all fields', () => {
    const raw = {
      type: 'simulation_update',
      cars: [
        { id: 1, position: [32.5, -117.0], velocity: 5.5, status: 0, queue_id: null, queue_position: null },
        { id: 2, position: [32.6, -117.1], velocity: 10.0, status: 1, queue_id: 0, queue_position: 1 },
        { id: 3, position: [32.7, -117.2], velocity: 0.0, status: 2, queue_id: 1, queue_position: 1 },
      ],
      metrics: {
        total_arrivals: 100,
        total_completions: 50,
        average_wait_time: 120.5,
        simulation_time: 3600.0,
      },
      service_nodes: [
        { node_id: 'booth_1', queue_id: 0, is_busy: true, current_car_id: 2, service_rate: 3.0, total_served: 25 },
        { node_id: 'booth_2', queue_id: 1, is_busy: true, current_car_id: 3, service_rate: 2.5, total_served: 25 },
      ],
      timestamp: 1234567890.123,
    };

    const parsed = parseServerMessage(raw);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('simulation_update');

    if (parsed?.type === 'simulation_update') {
      expect(parsed.cars.length).toBe(3);
      expect(parsed.service_nodes.length).toBe(2);
      expect(parsed.metrics.total_arrivals).toBe(100);
      expect(parsed.timestamp).toBe(1234567890.123);
    }
  });

  it('should handle empty cars array', () => {
    const raw = {
      type: 'simulation_update',
      cars: [],
      metrics: {
        total_arrivals: 0,
        total_completions: 0,
        average_wait_time: null,
        simulation_time: 0.0,
      },
      service_nodes: [],
      timestamp: 0.0,
    };

    const parsed = parseServerMessage(raw);
    expect(parsed?.type).toBe('simulation_update');
    if (parsed?.type === 'simulation_update') {
      expect(parsed.cars.length).toBe(0);
    }
  });

  it('should preserve all car fields correctly', () => {
    const car: CarState = {
      id: 42,
      position: [32.12345, -117.54321],
      velocity: 15.5,
      status: 1,
      queue_id: 2,
      queue_position: 5,
    };

    const raw = {
      type: 'simulation_update',
      cars: [car],
      metrics: { total_arrivals: 1, total_completions: 0, average_wait_time: null, simulation_time: 10.0 },
      service_nodes: [],
      timestamp: 100.0,
    };

    const parsed = parseServerMessage(raw);
    if (parsed?.type === 'simulation_update') {
      expect(parsed.cars[0].id).toBe(42);
      expect(parsed.cars[0].position[0]).toBeCloseTo(32.12345);
      expect(parsed.cars[0].position[1]).toBeCloseTo(-117.54321);
      expect(parsed.cars[0].velocity).toBeCloseTo(15.5);
      expect(parsed.cars[0].status).toBe(1);
      expect(parsed.cars[0].queue_id).toBe(2);
      expect(parsed.cars[0].queue_position).toBe(5);
    }
  });
});

// ============================================================================
// Control Message Tests (7.8)
// ============================================================================

describe('Control message sending', () => {
  it('should create a pause control message', () => {
    const msg = createControlMessage.pause();
    expect(msg.type).toBe('control');
    expect((msg as any).action).toBe('pause');
  });

  it('should create a resume control message', () => {
    const msg = createControlMessage.resume();
    expect(msg.type).toBe('control');
    expect((msg as any).action).toBe('resume');
  });

  it('should create a setTimeSpeed control message', () => {
    const msg = createControlMessage.setTimeSpeed(2.5);
    expect(msg.type).toBe('control');
    expect((msg as any).action).toBe('set_time_speed');
    expect((msg as any).speed).toBe(2.5);
  });

  it('should create an addStation control message', () => {
    const msg = createControlMessage.addStation(3);
    expect(msg.type).toBe('control');
    expect((msg as any).action).toBe('add_station');
    expect((msg as any).queue_id).toBe(3);
  });

  it('should create a removeStation control message', () => {
    const msg = createControlMessage.removeStation('booth_5');
    expect(msg.type).toBe('control');
    expect((msg as any).action).toBe('remove_station');
    expect((msg as any).node_id).toBe('booth_5');
  });

  it('should create a heartbeat message', () => {
    const msg = createHeartbeatMessage();
    expect(msg.type).toBe('heartbeat');
  });

  it('should create a requestFullState message', () => {
    const msg = createRequestFullStateMessage();
    expect(msg.type).toBe('request_full_state');
  });

  it('should serialize control messages to MessagePack', () => {
    const msg = createControlMessage.setTimeSpeed(5.0);
    const encoded = encode(msg);
    expect(encoded).toBeInstanceOf(Uint8Array);

    const decoded = decode(encoded) as ClientMessage;
    expect(decoded.type).toBe('control');
    expect((decoded as any).speed).toBe(5.0);
  });
});

// ============================================================================
// MessagePack Size Efficiency Tests
// ============================================================================

describe('MessagePack size efficiency', () => {
  it('should produce smaller binary than JSON for simulation updates', () => {
    // Generate a large dataset similar to real simulation (5000 cars)
    const message = {
      type: 'simulation_update',
      cars: Array.from({ length: 5000 }, (_, i) => ({
        id: i,
        position: [32.5 + i * 0.0001, -117.0 + i * 0.0001],
        velocity: 10.0 + i * 0.01,
        status: i % 4,
        queue_id: i % 2 === 0 ? i % 3 : null,
        queue_position: i % 2 === 0 ? i : null,
      })),
      metrics: {
        total_arrivals: 5000,
        total_completions: 2500,
        average_wait_time: 180.5,
        simulation_time: 7200.0,
      },
      service_nodes: Array.from({ length: 10 }, (_, i) => ({
        node_id: `booth_${i}`,
        queue_id: i % 3,
        is_busy: i % 2 === 0,
        current_car_id: i % 2 === 0 ? i : null,
        service_rate: 3.0,
        total_served: 250,
      })),
      timestamp: 1234567890.123,
    };

    const msgpackBytes = encode(message);
    const jsonString = JSON.stringify(message);

    // MessagePack should be smaller than JSON
    expect(msgpackBytes.length).toBeLessThan(jsonString.length);

    // At scale, MessagePack is more efficient but exact ratio depends on data structure
    // With deeply nested objects and many strings, ratio is typically 70-90%
    const ratio = msgpackBytes.length / jsonString.length;
    expect(ratio).toBeLessThan(0.95); // At minimum, should be smaller
  });

  it('should produce smaller binary for position-only updates', () => {
    const message = {
      type: 'position_only',
      positions: Array.from({ length: 1000 }, (_, i) => [
        i,
        32.5 + i * 0.0001,
        -117.0 + i * 0.0001,
      ]),
      timestamp: 1234567890.123,
    };

    const msgpackBytes = encode(message);
    const jsonString = JSON.stringify(message);

    expect(msgpackBytes.length).toBeLessThan(jsonString.length);
  });
});

// ============================================================================
// Binary/JSON Auto-detection Tests
// ============================================================================

describe('Binary vs JSON message format detection', () => {
  it('should detect binary data (ArrayBuffer/Uint8Array)', () => {
    const binaryData = encode({ type: 'heartbeat' });
    expect(binaryData instanceof Uint8Array).toBe(true);

    // Simulate WebSocket binary message
    const arrayBuffer = binaryData.buffer.slice(
      binaryData.byteOffset,
      binaryData.byteOffset + binaryData.byteLength
    );
    expect(arrayBuffer instanceof ArrayBuffer).toBe(true);
  });

  it('should handle JSON string messages (Python backend compatibility)', () => {
    const jsonMessage = JSON.stringify({
      type: 'simulation_update',
      data: {
        cars: [],
        queues: [],
        metrics: { total_arrivals: 0, total_completions: 0 },
      },
    });

    // This is how Python backend sends messages
    expect(typeof jsonMessage).toBe('string');

    const parsed = JSON.parse(jsonMessage);
    expect(parsed.type).toBe('simulation_update');
  });
});

// ============================================================================
// Reconnection Logic Tests (7.6)
// ============================================================================

import { calculateBackoffDelay, isBinaryMessage } from './websocket';

describe('Reconnection with exponential backoff', () => {
  it('should calculate exponential backoff delay correctly', () => {
    // Initial delay
    expect(calculateBackoffDelay(0, 1000, 30000)).toBe(1000);
    // First retry: 2^1 * 1000 = 2000
    expect(calculateBackoffDelay(1, 1000, 30000)).toBe(2000);
    // Second retry: 2^2 * 1000 = 4000
    expect(calculateBackoffDelay(2, 1000, 30000)).toBe(4000);
    // Third retry: 2^3 * 1000 = 8000
    expect(calculateBackoffDelay(3, 1000, 30000)).toBe(8000);
    // Fourth retry: 2^4 * 1000 = 16000
    expect(calculateBackoffDelay(4, 1000, 30000)).toBe(16000);
    // Fifth retry: 2^5 * 1000 = 32000, but max is 30000
    expect(calculateBackoffDelay(5, 1000, 30000)).toBe(30000);
    // Subsequent retries should cap at max
    expect(calculateBackoffDelay(10, 1000, 30000)).toBe(30000);
  });

  it('should respect custom initial delay', () => {
    expect(calculateBackoffDelay(0, 500, 30000)).toBe(500);
    expect(calculateBackoffDelay(1, 500, 30000)).toBe(1000);
    expect(calculateBackoffDelay(2, 500, 30000)).toBe(2000);
  });

  it('should respect custom max delay', () => {
    expect(calculateBackoffDelay(10, 1000, 5000)).toBe(5000);
    expect(calculateBackoffDelay(5, 1000, 10000)).toBe(10000);
  });
});

describe('Binary message detection utility', () => {
  it('should detect ArrayBuffer as binary', () => {
    const buffer = new ArrayBuffer(8);
    expect(isBinaryMessage(buffer)).toBe(true);
  });

  it('should not detect string as binary', () => {
    expect(isBinaryMessage('hello')).toBe(false);
  });

  it('should not detect Uint8Array as binary (only ArrayBuffer)', () => {
    const uint8 = new Uint8Array(8);
    expect(isBinaryMessage(uint8)).toBe(false);
  });

  it('should not detect objects as binary', () => {
    expect(isBinaryMessage({})).toBe(false);
    expect(isBinaryMessage(null)).toBe(false);
    expect(isBinaryMessage(undefined)).toBe(false);
  });
});

// ============================================================================
// High Frequency Update Tests (7.10)
// ============================================================================

describe('High frequency update handling', () => {
  it('should parse 100 messages in under 100ms (10Hz performance)', () => {
    const messages: unknown[] = [];

    // Generate 100 simulation updates (10 seconds at 10Hz)
    for (let i = 0; i < 100; i++) {
      messages.push({
        type: 'simulation_update',
        cars: Array.from({ length: 100 }, (_, j) => ({
          id: j,
          position: [32.5 + j * 0.001, -117.0 + j * 0.001],
          velocity: 10.0,
          status: j % 4,
          queue_id: null,
          queue_position: null,
        })),
        metrics: {
          total_arrivals: i,
          total_completions: Math.floor(i / 2),
          average_wait_time: 120.5,
          simulation_time: i * 0.1,
        },
        service_nodes: [],
        timestamp: Date.now() / 1000 + i * 0.1,
      });
    }

    // Encode all messages to MessagePack
    const encodedMessages = messages.map((msg) => encode(msg));

    // Time the decoding and parsing
    const startTime = performance.now();

    for (const encoded of encodedMessages) {
      const decoded = decode(encoded);
      const parsed = parseServerMessage(decoded);
      expect(parsed).not.toBeNull();
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;

    console.log(`Parsed 100 messages in ${totalTime.toFixed(2)}ms (${(totalTime / 100).toFixed(3)}ms per message)`);

    // Should complete in under 100ms for smooth 10Hz updates
    expect(totalTime).toBeLessThan(100);
  });

  it('should handle 1000 position-only updates efficiently', () => {
    const messages: unknown[] = [];

    // Generate 1000 position-only updates (about 33 seconds at 30Hz)
    for (let i = 0; i < 1000; i++) {
      messages.push({
        type: 'position_only',
        positions: Array.from({ length: 100 }, (_, j) => [
          j,
          32.5 + j * 0.001 + i * 0.0001,
          -117.0 + j * 0.001 + i * 0.0001,
        ]),
        timestamp: Date.now() / 1000 + i * 0.033,
      });
    }

    const encodedMessages = messages.map((msg) => encode(msg));

    const startTime = performance.now();

    for (const encoded of encodedMessages) {
      const decoded = decode(encoded);
      const parsed = parseServerMessage(decoded);
      expect(parsed?.type).toBe('position_only');
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;

    console.log(`Parsed 1000 position-only messages in ${totalTime.toFixed(2)}ms (${(totalTime / 1000).toFixed(3)}ms per message)`);

    // Should handle 30Hz updates without issues
    expect(totalTime).toBeLessThan(1000); // 1 second for 1000 messages
  });
});
