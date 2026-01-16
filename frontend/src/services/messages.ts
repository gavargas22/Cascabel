/**
 * WebSocket message types matching Rust backend (rust-api/src/api/messages.rs)
 *
 * These types define the structure of MessagePack and JSON messages
 * exchanged between the frontend and Rust backend via WebSocket.
 */

// ============================================================================
// Car Status enum matching Rust backend
// ============================================================================

export type CarStatus = 'approaching' | 'queued' | 'serving' | 'completed' | 'unknown';

export const CarStatusCode = {
  APPROACHING: 0,
  QUEUED: 1,
  SERVING: 2,
  COMPLETED: 3,
} as const;

export function carStatusFromCode(code: number): CarStatus {
  switch (code) {
    case 0: return 'approaching';
    case 1: return 'queued';
    case 2: return 'serving';
    case 3: return 'completed';
    default: return 'unknown';
  }
}

export function carStatusToCode(status: CarStatus): number {
  switch (status) {
    case 'approaching': return 0;
    case 'queued': return 1;
    case 'serving': return 2;
    case 'completed': return 3;
    default: return -1;
  }
}

// ============================================================================
// Server-to-Client Message Types
// ============================================================================

/**
 * Car state for full updates
 * Maps to Rust CarState struct
 */
export interface CarState {
  /** Unique car ID */
  id: number;
  /** GPS position as [latitude, longitude] */
  position: [number, number];
  /** Current velocity in m/s */
  velocity: number;
  /** Status code: 0=approaching, 1=queued, 2=serving, 3=completed */
  status: number;
  /** Queue ID (if assigned) */
  queue_id?: number | null;
  /** Position in queue (1=front) */
  queue_position?: number | null;
}

/**
 * Metrics update message
 * Maps to Rust MetricsUpdate struct
 */
export interface MetricsUpdate {
  /** Total number of car arrivals */
  total_arrivals: number;
  /** Total number of completed services */
  total_completions: number;
  /** Average wait time in seconds (null if no data) */
  average_wait_time: number | null;
  /** Current simulation time in seconds */
  simulation_time: number;
}

/**
 * Service node state
 * Maps to Rust ServiceNodeState struct
 */
export interface ServiceNodeState {
  /** Node identifier */
  node_id: string;
  /** Queue this node belongs to */
  queue_id: number;
  /** Whether the node is currently serving */
  is_busy: boolean;
  /** ID of car being served (if any) */
  current_car_id?: number | null;
  /** Service rate (cars per minute) */
  service_rate: number;
  /** Total cars served */
  total_served: number;
}

/**
 * Full simulation update containing all car states and metrics
 * Maps to Rust SimulationUpdate struct
 */
export interface SimulationUpdate {
  /** Current state of all cars */
  cars: CarState[];
  /** Current metrics */
  metrics: MetricsUpdate;
  /** Service node states */
  service_nodes: ServiceNodeState[];
  /** Timestamp in seconds since epoch */
  timestamp: number;
}

/**
 * Compact position-only update for high-frequency streaming
 * Maps to Rust PositionOnlyUpdate struct
 * Each position is (car_id, latitude, longitude)
 */
export interface PositionOnlyUpdate {
  /** Position tuples: [car_id, latitude, longitude][] */
  positions: [number, number, number][];
  /** Timestamp in seconds since epoch */
  timestamp: number;
}

/**
 * Error message from server
 * Maps to Rust ErrorMessage struct
 */
export interface ErrorMessage {
  /** Error code */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Additional details */
  details?: string | null;
}

/**
 * Server-to-client message types (tagged union)
 * Maps to Rust ServerMessage enum
 */
export type ServerMessage =
  | { type: 'simulation_update' } & SimulationUpdate
  | { type: 'position_only' } & PositionOnlyUpdate
  | { type: 'metrics' } & MetricsUpdate
  | { type: 'error' } & ErrorMessage
  | { type: 'heartbeat' }
  | { type: 'ack'; message_id?: string | null };

// ============================================================================
// Client-to-Server Message Types
// ============================================================================

/**
 * Control message actions
 * Maps to Rust ControlMessage enum
 */
export type ControlMessage =
  | { action: 'pause' }
  | { action: 'resume' }
  | { action: 'set_time_speed'; speed: number }
  | { action: 'add_station'; queue_id: number }
  | { action: 'remove_station'; node_id: string };

/**
 * Client-to-server message types (tagged union)
 * Maps to Rust ClientMessage enum
 */
export type ClientMessage =
  | { type: 'control' } & ControlMessage
  | { type: 'heartbeat' }
  | { type: 'request_full_state' };

// ============================================================================
// Type Guards
// ============================================================================

export function isSimulationUpdate(msg: ServerMessage): msg is { type: 'simulation_update' } & SimulationUpdate {
  return msg.type === 'simulation_update';
}

export function isPositionOnlyUpdate(msg: ServerMessage): msg is { type: 'position_only' } & PositionOnlyUpdate {
  return msg.type === 'position_only';
}

export function isMetricsUpdate(msg: ServerMessage): msg is { type: 'metrics' } & MetricsUpdate {
  return msg.type === 'metrics';
}

export function isErrorMessage(msg: ServerMessage): msg is { type: 'error' } & ErrorMessage {
  return msg.type === 'error';
}

export function isHeartbeat(msg: ServerMessage): msg is { type: 'heartbeat' } {
  return msg.type === 'heartbeat';
}

export function isAck(msg: ServerMessage): msg is { type: 'ack'; message_id?: string | null } {
  return msg.type === 'ack';
}

// ============================================================================
// Conversion Helpers
// ============================================================================

/**
 * Convert CarState to a display-friendly format with status string
 */
export function carStateToDisplayFormat(car: CarState): {
  id: number;
  position: [number, number];
  velocity: number;
  status: CarStatus;
  queue_id?: number;
  queue_position?: number;
} {
  return {
    id: car.id,
    position: car.position,
    velocity: car.velocity,
    status: carStatusFromCode(car.status),
    queue_id: car.queue_id ?? undefined,
    queue_position: car.queue_position ?? undefined,
  };
}

/**
 * Convert raw MessagePack decoded object to proper ServerMessage type.
 * Handles the serde tag format from Rust.
 */
export function parseServerMessage(raw: unknown): ServerMessage | null {
  if (typeof raw !== 'object' || raw === null) {
    return null;
  }

  const obj = raw as Record<string, unknown>;
  const type = obj.type;

  if (typeof type !== 'string') {
    return null;
  }

  switch (type) {
    case 'simulation_update':
      return {
        type: 'simulation_update',
        cars: (obj.cars as CarState[]) || [],
        metrics: obj.metrics as MetricsUpdate,
        service_nodes: (obj.service_nodes as ServiceNodeState[]) || [],
        timestamp: (obj.timestamp as number) || 0,
      };

    case 'position_only':
      return {
        type: 'position_only',
        positions: (obj.positions as [number, number, number][]) || [],
        timestamp: (obj.timestamp as number) || 0,
      };

    case 'metrics':
      return {
        type: 'metrics',
        total_arrivals: (obj.total_arrivals as number) || 0,
        total_completions: (obj.total_completions as number) || 0,
        average_wait_time: obj.average_wait_time as number | null,
        simulation_time: (obj.simulation_time as number) || 0,
      };

    case 'error':
      return {
        type: 'error',
        code: (obj.code as string) || 'UNKNOWN',
        message: (obj.message as string) || 'Unknown error',
        details: obj.details as string | null,
      };

    case 'heartbeat':
      return { type: 'heartbeat' };

    case 'ack':
      return {
        type: 'ack',
        message_id: obj.message_id as string | null,
      };

    default:
      console.warn('Unknown server message type:', type);
      return null;
  }
}

/**
 * Create control messages
 */
export const createControlMessage = {
  pause: (): ClientMessage => ({ type: 'control', action: 'pause' }),
  resume: (): ClientMessage => ({ type: 'control', action: 'resume' }),
  setTimeSpeed: (speed: number): ClientMessage => ({ type: 'control', action: 'set_time_speed', speed }),
  addStation: (queueId: number): ClientMessage => ({ type: 'control', action: 'add_station', queue_id: queueId }),
  removeStation: (nodeId: string): ClientMessage => ({ type: 'control', action: 'remove_station', node_id: nodeId }),
};

export const createHeartbeatMessage = (): ClientMessage => ({ type: 'heartbeat' });

export const createRequestFullStateMessage = (): ClientMessage => ({ type: 'request_full_state' });
