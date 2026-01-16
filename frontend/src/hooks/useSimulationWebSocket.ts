/**
 * React Hook for Simulation WebSocket Connection
 *
 * Provides a React-friendly interface to the binary WebSocket client
 * with automatic state management and cleanup.
 *
 * Features:
 * - Automatic connection/disconnection on mount/unmount
 * - Connection state tracking
 * - Simulation data state management
 * - Control actions (pause, resume, speed change)
 * - Support for both binary (Rust) and JSON (Python) backends
 *
 * @module useSimulationWebSocket
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  WebSocketClient,
  WebSocketClientConfig,
  ConnectionState,
  createWebSocketClient,
} from '../services/websocket';
import {
  ServerMessage,
  CarState,
  MetricsUpdate,
  ServiceNodeState,
  carStatusFromCode,
  CarStatus,
} from '../services/messages';

// ============================================================================
// Types
// ============================================================================

/** Configuration options for the hook */
export interface UseSimulationWebSocketConfig {
  /** Base URL for WebSocket (default: ws://localhost:8000) */
  baseUrl?: string;
  /** Use binary MessagePack protocol (default: true) */
  useBinary?: boolean;
  /** Auto-connect when simulationId is provided (default: true) */
  autoConnect?: boolean;
  /** Enable automatic reconnection (default: true) */
  autoReconnect?: boolean;
}

/** Car data with status as string for UI display */
export interface DisplayCarState {
  id: number;
  position: [number, number];
  velocity: number;
  status: CarStatus;
  queue_id?: number;
  queue_position?: number;
}

/** Simulation state returned by the hook */
export interface SimulationState {
  /** All cars in the simulation */
  cars: DisplayCarState[];
  /** Current simulation metrics */
  metrics: MetricsUpdate | null;
  /** Service node states */
  serviceNodes: ServiceNodeState[];
  /** Last update timestamp */
  timestamp: number;
}

/** Return type of the useSimulationWebSocket hook */
export interface UseSimulationWebSocketReturn {
  /** Current connection state */
  connectionState: ConnectionState;
  /** Current simulation data */
  simulationState: SimulationState | null;
  /** Whether currently connected */
  isConnected: boolean;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
  /** Error message if any */
  error: string | null;
  /** Connect to simulation */
  connect: () => void;
  /** Disconnect from simulation */
  disconnect: () => void;
  /** Pause simulation */
  pause: () => boolean;
  /** Resume simulation */
  resume: () => boolean;
  /** Set simulation time speed */
  setTimeSpeed: (speed: number) => boolean;
  /** Add a service station */
  addStation: (queueId: number) => boolean;
  /** Remove a service station */
  removeStation: (nodeId: string) => boolean;
  /** Request full state update */
  requestFullState: () => boolean;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_CONFIG: Required<UseSimulationWebSocketConfig> = {
  baseUrl: 'ws://localhost:8000', // Default to Rust backend
  useBinary: true,
  autoConnect: true,
  autoReconnect: true,
};

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * React hook for managing WebSocket connection to simulation server.
 *
 * @param simulationId - The simulation ID to connect to (null to disconnect)
 * @param config - Configuration options
 * @returns Simulation state and control functions
 *
 * @example
 * ```tsx
 * function SimulationView({ simulationId }) {
 *   const {
 *     connectionState,
 *     simulationState,
 *     isConnected,
 *     pause,
 *     resume,
 *     setTimeSpeed,
 *   } = useSimulationWebSocket(simulationId);
 *
 *   if (!isConnected) {
 *     return <div>Connecting...</div>;
 *   }
 *
 *   return (
 *     <div>
 *       <p>Cars: {simulationState?.cars.length || 0}</p>
 *       <button onClick={pause}>Pause</button>
 *       <button onClick={resume}>Resume</button>
 *       <button onClick={() => setTimeSpeed(2)}>2x Speed</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useSimulationWebSocket(
  simulationId: string | null,
  config: UseSimulationWebSocketConfig = {}
): UseSimulationWebSocketReturn {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [simulationState, setSimulationState] = useState<SimulationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const clientRef = useRef<WebSocketClient | null>(null);
  const simulationIdRef = useRef<string | null>(null);

  // Convert CarState array to DisplayCarState array
  const convertCars = useCallback((cars: CarState[]): DisplayCarState[] => {
    return cars.map((car) => ({
      id: car.id,
      position: car.position,
      velocity: car.velocity,
      status: carStatusFromCode(car.status),
      queue_id: car.queue_id ?? undefined,
      queue_position: car.queue_position ?? undefined,
    }));
  }, []);

  // Handle simulation update
  const handleSimulationUpdate = useCallback(
    (update: ServerMessage & { type: 'simulation_update' }) => {
      setSimulationState({
        cars: convertCars(update.cars),
        metrics: update.metrics,
        serviceNodes: update.service_nodes,
        timestamp: update.timestamp,
      });
      setError(null);
    },
    [convertCars]
  );

  // Handle position-only update (merge with existing state)
  const handlePositionUpdate = useCallback(
    (update: ServerMessage & { type: 'position_only' }) => {
      setSimulationState((prev) => {
        if (!prev) return prev;

        // Create a map of new positions
        const positionMap = new Map<number, [number, number]>();
        for (const [id, lat, lon] of update.positions) {
          positionMap.set(id, [lat, lon]);
        }

        // Update car positions
        const updatedCars = prev.cars.map((car) => {
          const newPosition = positionMap.get(car.id);
          if (newPosition) {
            return { ...car, position: newPosition };
          }
          return car;
        });

        return {
          ...prev,
          cars: updatedCars,
          timestamp: update.timestamp,
        };
      });
    },
    []
  );

  // Handle metrics update
  const handleMetricsUpdate = useCallback(
    (update: ServerMessage & { type: 'metrics' }) => {
      setSimulationState((prev) => {
        if (!prev) {
          return {
            cars: [],
            metrics: update,
            serviceNodes: [],
            timestamp: Date.now() / 1000,
          };
        }
        return {
          ...prev,
          metrics: update,
        };
      });
    },
    []
  );

  // Handle error message
  const handleError = useCallback((errorMsg: ServerMessage & { type: 'error' }) => {
    console.error('[useSimulationWebSocket] Server error:', errorMsg);
    setError(`${errorMsg.code}: ${errorMsg.message}`);
  }, []);

  // Handle state change
  const handleStateChange = useCallback((state: ConnectionState) => {
    setConnectionState(state);
    if (state === 'connected') {
      setError(null);
    }
  }, []);

  // Handle WebSocket error
  const handleWebSocketError = useCallback((event: Event) => {
    console.error('[useSimulationWebSocket] WebSocket error:', event);
    setError('WebSocket connection error');
  }, []);

  // Create and configure client
  useEffect(() => {
    // Clean up previous client if simulation ID changed
    if (simulationIdRef.current !== simulationId) {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
      simulationIdRef.current = simulationId;
    }

    // No simulation ID - stay disconnected
    if (!simulationId) {
      setConnectionState('disconnected');
      setSimulationState(null);
      return;
    }

    // Create new client
    const client = createWebSocketClient({
      baseUrl: mergedConfig.baseUrl,
      simulationId,
      useBinary: mergedConfig.useBinary,
      autoReconnect: mergedConfig.autoReconnect,
    });

    client.setHandlers({
      onStateChange: handleStateChange,
      onSimulationUpdate: handleSimulationUpdate,
      onPositionUpdate: handlePositionUpdate,
      onMetricsUpdate: handleMetricsUpdate,
      onError: handleError,
      onWebSocketError: handleWebSocketError,
    });

    clientRef.current = client;

    // Auto-connect if enabled
    if (mergedConfig.autoConnect) {
      client.connect();
    }

    // Cleanup on unmount or simulationId change
    return () => {
      client.disconnect();
    };
  }, [
    simulationId,
    mergedConfig.baseUrl,
    mergedConfig.useBinary,
    mergedConfig.autoConnect,
    mergedConfig.autoReconnect,
    handleStateChange,
    handleSimulationUpdate,
    handlePositionUpdate,
    handleMetricsUpdate,
    handleError,
    handleWebSocketError,
  ]);

  // Update reconnect attempts from client
  useEffect(() => {
    const interval = setInterval(() => {
      if (clientRef.current) {
        setReconnectAttempts(clientRef.current.getReconnectAttempts());
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Control functions
  const connect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    setSimulationState(null);
  }, []);

  const pause = useCallback((): boolean => {
    return clientRef.current?.pause() ?? false;
  }, []);

  const resume = useCallback((): boolean => {
    return clientRef.current?.resume() ?? false;
  }, []);

  const setTimeSpeed = useCallback((speed: number): boolean => {
    return clientRef.current?.setTimeSpeed(speed) ?? false;
  }, []);

  const addStation = useCallback((queueId: number): boolean => {
    return clientRef.current?.addStation(queueId) ?? false;
  }, []);

  const removeStation = useCallback((nodeId: string): boolean => {
    return clientRef.current?.removeStation(nodeId) ?? false;
  }, []);

  const requestFullState = useCallback((): boolean => {
    return clientRef.current?.requestFullState() ?? false;
  }, []);

  // Derived state
  const isConnected = connectionState === 'connected';

  return {
    connectionState,
    simulationState,
    isConnected,
    reconnectAttempts,
    error,
    connect,
    disconnect,
    pause,
    resume,
    setTimeSpeed,
    addStation,
    removeStation,
    requestFullState,
  };
}

// ============================================================================
// Utility Hook for Python Backend Compatibility
// ============================================================================

/**
 * Hook variant configured for Python backend (JSON messages)
 */
export function useSimulationWebSocketPython(
  simulationId: string | null,
  config: Omit<UseSimulationWebSocketConfig, 'useBinary' | 'baseUrl'> = {}
): UseSimulationWebSocketReturn {
  return useSimulationWebSocket(simulationId, {
    ...config,
    baseUrl: 'ws://localhost:8000',
    useBinary: false,
  });
}

/**
 * Hook variant configured for Rust backend (binary MessagePack)
 */
export function useSimulationWebSocketRust(
  simulationId: string | null,
  config: Omit<UseSimulationWebSocketConfig, 'useBinary' | 'baseUrl'> = {}
): UseSimulationWebSocketReturn {
  return useSimulationWebSocket(simulationId, {
    ...config,
    baseUrl: 'ws://localhost:8000',
    useBinary: true,
  });
}
