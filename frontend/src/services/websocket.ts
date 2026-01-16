/**
 * Binary WebSocket Client for Cascabel Simulation
 *
 * Features:
 * - MessagePack binary protocol support (Rust backend)
 * - JSON fallback for Python backend compatibility
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Heartbeat mechanism for stale connection detection
 * - Control message sending (pause, resume, time speed)
 *
 * @module websocket
 */

import { encode, decode } from '@msgpack/msgpack';
import {
  ServerMessage,
  ClientMessage,
  parseServerMessage,
  createHeartbeatMessage,
  createRequestFullStateMessage,
  isSimulationUpdate,
  isPositionOnlyUpdate,
  isMetricsUpdate,
  isErrorMessage,
  isHeartbeat,
  isAck,
} from './messages';

// ============================================================================
// Types and Interfaces
// ============================================================================

/** Connection states for the WebSocket client */
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

/** Configuration options for the WebSocket client */
export interface WebSocketClientConfig {
  /** Base URL for WebSocket connection (e.g., ws://localhost:8000) */
  baseUrl: string;
  /** Simulation ID to connect to */
  simulationId: string;
  /** Use binary MessagePack protocol (default: true for Rust backend) */
  useBinary?: boolean;
  /** Enable automatic reconnection (default: true) */
  autoReconnect?: boolean;
  /** Initial reconnect delay in ms (default: 1000) */
  initialReconnectDelay?: number;
  /** Maximum reconnect delay in ms (default: 30000) */
  maxReconnectDelay?: number;
  /** Maximum reconnection attempts (default: 10) */
  maxReconnectAttempts?: number;
  /** Heartbeat interval in ms (default: 30000) */
  heartbeatInterval?: number;
  /** Heartbeat timeout in ms - if no response, connection is considered stale (default: 10000) */
  heartbeatTimeout?: number;
}

/** Event handlers for WebSocket client */
export interface WebSocketClientHandlers {
  /** Called when connection state changes */
  onStateChange?: (state: ConnectionState) => void;
  /** Called when a simulation update is received */
  onSimulationUpdate?: (update: ServerMessage & { type: 'simulation_update' }) => void;
  /** Called when a position-only update is received */
  onPositionUpdate?: (update: ServerMessage & { type: 'position_only' }) => void;
  /** Called when a metrics update is received */
  onMetricsUpdate?: (update: ServerMessage & { type: 'metrics' }) => void;
  /** Called when an error message is received from server */
  onError?: (error: ServerMessage & { type: 'error' }) => void;
  /** Called when a WebSocket error occurs */
  onWebSocketError?: (error: Event) => void;
  /** Called when an ack message is received */
  onAck?: (ack: ServerMessage & { type: 'ack' }) => void;
  /** Called on any received message (for debugging) */
  onMessage?: (message: ServerMessage) => void;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_CONFIG: Required<Omit<WebSocketClientConfig, 'baseUrl' | 'simulationId'>> = {
  useBinary: true,
  autoReconnect: true,
  initialReconnectDelay: 1000,
  maxReconnectDelay: 30000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  heartbeatTimeout: 10000,
};

// ============================================================================
// WebSocketClient Class
// ============================================================================

/**
 * Binary WebSocket client for real-time simulation updates.
 *
 * Supports both MessagePack (Rust backend) and JSON (Python backend) protocols
 * with automatic format detection.
 *
 * @example
 * ```typescript
 * const client = new WebSocketClient({
 *   baseUrl: 'ws://localhost:8000',
 *   simulationId: 'abc123',
 * });
 *
 * client.setHandlers({
 *   onSimulationUpdate: (update) => {
 *     console.log('Cars:', update.cars.length);
 *   },
 *   onStateChange: (state) => {
 *     console.log('Connection state:', state);
 *   },
 * });
 *
 * client.connect();
 * ```
 */
export class WebSocketClient {
  private config: Required<WebSocketClientConfig>;
  private handlers: WebSocketClientHandlers = {};
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeoutTimer: ReturnType<typeof setTimeout> | null = null;
  private lastHeartbeatResponse: number = 0;
  private isManualDisconnect = false;

  constructor(config: WebSocketClientConfig) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
    };
  }

  // ==========================================================================
  // Public API
  // ==========================================================================

  /**
   * Set event handlers for the client
   */
  setHandlers(handlers: WebSocketClientHandlers): void {
    this.handlers = { ...this.handlers, ...handlers };
  }

  /**
   * Get the current connection state
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.state === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      console.warn('WebSocket already connected or connecting');
      return;
    }

    this.isManualDisconnect = false;
    this.reconnectAttempts = 0;
    this.doConnect();
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.isManualDisconnect = true;
    this.cleanup();
    this.setState('disconnected');
  }

  /**
   * Send a control message to the server
   */
  sendControlMessage(message: ClientMessage): boolean {
    return this.send(message);
  }

  /**
   * Send a pause command
   */
  pause(): boolean {
    return this.send({ type: 'control', action: 'pause' });
  }

  /**
   * Send a resume command
   */
  resume(): boolean {
    return this.send({ type: 'control', action: 'resume' });
  }

  /**
   * Set simulation time speed
   */
  setTimeSpeed(speed: number): boolean {
    return this.send({ type: 'control', action: 'set_time_speed', speed });
  }

  /**
   * Add a service station to a queue
   */
  addStation(queueId: number): boolean {
    return this.send({ type: 'control', action: 'add_station', queue_id: queueId });
  }

  /**
   * Remove a service station
   */
  removeStation(nodeId: string): boolean {
    return this.send({ type: 'control', action: 'remove_station', node_id: nodeId });
  }

  /**
   * Request full simulation state (useful after reconnection)
   */
  requestFullState(): boolean {
    return this.send(createRequestFullStateMessage());
  }

  /**
   * Get current reconnection attempt count
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  // ==========================================================================
  // Private Methods
  // ==========================================================================

  private doConnect(): void {
    this.setState('connecting');

    const url = `${this.config.baseUrl}/ws/${this.config.simulationId}`;
    console.log(`[WebSocket] Connecting to ${url}`);

    try {
      this.ws = new WebSocket(url);

      // Request binary data if using MessagePack
      if (this.config.useBinary) {
        this.ws.binaryType = 'arraybuffer';
      }

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      this.setState('error');
      this.scheduleReconnect();
    }
  }

  private handleOpen(): void {
    console.log('[WebSocket] Connected');
    this.setState('connected');
    this.reconnectAttempts = 0;
    this.lastHeartbeatResponse = Date.now();
    this.startHeartbeat();

    // Request full state after reconnection
    if (this.reconnectAttempts > 0) {
      console.log('[WebSocket] Requesting full state after reconnection');
      this.requestFullState();
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      let message: ServerMessage | null;

      if (event.data instanceof ArrayBuffer) {
        // Binary MessagePack data from Rust backend
        const decoded = decode(new Uint8Array(event.data));
        message = parseServerMessage(decoded);
      } else if (typeof event.data === 'string') {
        // JSON string from Python backend
        const parsed = JSON.parse(event.data);
        message = parseServerMessage(parsed);
      } else {
        console.warn('[WebSocket] Unknown message format:', typeof event.data);
        return;
      }

      if (!message) {
        console.warn('[WebSocket] Failed to parse message');
        return;
      }

      // Handle heartbeat response
      if (isHeartbeat(message)) {
        this.lastHeartbeatResponse = Date.now();
        this.clearHeartbeatTimeout();
        return;
      }

      // Call message-specific handlers
      if (isSimulationUpdate(message)) {
        this.handlers.onSimulationUpdate?.(message);
      } else if (isPositionOnlyUpdate(message)) {
        this.handlers.onPositionUpdate?.(message);
      } else if (isMetricsUpdate(message)) {
        this.handlers.onMetricsUpdate?.(message);
      } else if (isErrorMessage(message)) {
        this.handlers.onError?.(message);
      } else if (isAck(message)) {
        this.handlers.onAck?.(message);
      }

      // Call generic message handler
      this.handlers.onMessage?.(message);
    } catch (error) {
      console.error('[WebSocket] Error handling message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log(`[WebSocket] Closed: code=${event.code}, reason=${event.reason}`);
    this.cleanup();

    if (!this.isManualDisconnect && this.config.autoReconnect) {
      this.scheduleReconnect();
    } else {
      this.setState('disconnected');
    }
  }

  private handleError(event: Event): void {
    console.error('[WebSocket] Error:', event);
    this.handlers.onWebSocketError?.(event);
    this.setState('error');
  }

  private send(message: ClientMessage): boolean {
    if (!this.isConnected()) {
      console.warn('[WebSocket] Cannot send message - not connected');
      return false;
    }

    try {
      if (this.config.useBinary) {
        // Send as MessagePack binary
        const encoded = encode(message);
        this.ws!.send(encoded);
      } else {
        // Send as JSON string
        this.ws!.send(JSON.stringify(message));
      }
      return true;
    } catch (error) {
      console.error('[WebSocket] Error sending message:', error);
      return false;
    }
  }

  private setState(state: ConnectionState): void {
    if (this.state !== state) {
      this.state = state;
      this.handlers.onStateChange?.(state);
    }
  }

  private cleanup(): void {
    this.stopHeartbeat();
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;

      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
  }

  // ==========================================================================
  // Reconnection Logic with Exponential Backoff
  // ==========================================================================

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      this.setState('error');
      return;
    }

    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.config.initialReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.config.maxReconnectDelay
    );

    // Add jitter (10-20% random variation)
    const jitter = delay * (0.1 + Math.random() * 0.1);
    const finalDelay = delay + jitter;

    this.reconnectAttempts++;
    this.setState('reconnecting');

    console.log(
      `[WebSocket] Scheduling reconnect attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${Math.round(finalDelay)}ms`
    );

    this.reconnectTimer = setTimeout(() => {
      this.doConnect();
    }, finalDelay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ==========================================================================
  // Heartbeat Mechanism
  // ==========================================================================

  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (!this.isConnected()) {
        return;
      }

      // Check if last heartbeat was acknowledged
      const timeSinceLastResponse = Date.now() - this.lastHeartbeatResponse;
      if (timeSinceLastResponse > this.config.heartbeatInterval + this.config.heartbeatTimeout) {
        console.warn('[WebSocket] Heartbeat timeout - connection may be stale');
        this.ws?.close();
        return;
      }

      // Send heartbeat
      const sent = this.send(createHeartbeatMessage());
      if (sent) {
        // Set timeout for heartbeat response
        this.heartbeatTimeoutTimer = setTimeout(() => {
          console.warn('[WebSocket] Heartbeat response timeout');
          // Don't close immediately - the interval check will handle it
        }, this.config.heartbeatTimeout);
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearHeartbeatTimeout();
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create a new WebSocket client instance
 */
export function createWebSocketClient(config: WebSocketClientConfig): WebSocketClient {
  return new WebSocketClient(config);
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Detect if message is binary (ArrayBuffer) or text (string)
 */
export function isBinaryMessage(data: unknown): data is ArrayBuffer {
  return data instanceof ArrayBuffer;
}

/**
 * Calculate exponential backoff delay
 */
export function calculateBackoffDelay(
  attempt: number,
  initialDelay: number = 1000,
  maxDelay: number = 30000
): number {
  return Math.min(initialDelay * Math.pow(2, attempt), maxDelay);
}
