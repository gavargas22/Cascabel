const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');

// Types
export interface BorderCrossingConfig {
  num_queues: number;
  nodes_per_queue: number[];
  arrival_rate: number;
  service_rates: number[];
  queue_assignment: 'random' | 'shortest' | 'round_robin';
  safe_distance: number;
  max_queue_length: number;
}

export interface SimulationConfig {
  max_simulation_time: number;
  time_factor: number;
  enable_telemetry: boolean;
  enable_position_tracking: boolean;
}

export interface PhoneConfig {
  sampling_rate: number;
  gps_noise: { horizontal_accuracy: number; vertical_accuracy: number };
  accelerometer_noise: number;
  gyro_noise: number;
  device_orientation: 'portrait' | 'landscape';
}

export interface PhysicsConfig {
  min_speed_mps: number;  // Minimum speed (slowest car)
  max_speed_mps: number;  // Maximum speed (fastest car)
  safe_distance_meters: number;  // Distance between cars
  max_acceleration: number;  // m/s² - higher = more aggressive
  max_deceleration: number;  // m/s² - higher absolute = harder braking
}

export interface SimulationRequest {
  border_config: BorderCrossingConfig;
  simulation_config?: SimulationConfig;
  phone_config?: PhoneConfig;
  physics_config?: PhysicsConfig;
  geojson_path?: string;
}

export interface BorderCrossing {
  id: string;
  name: string;
  direction: string;
  path: string;
  description: string;
  start_point: [number, number];
  end_point: [number, number];
  geometry_type: string;
}

export interface SimulationStatus {
  simulation_id: string;
  status: string;
  progress: number;
  current_time: number;
  total_arrivals: number;
  total_completions: number;
  message?: string;
}

export interface Car {
  car_id: number;
  position: number;
  velocity: number;
  status: 'arriving' | 'queued' | 'serving' | 'completed';
  queue_id?: number;
}

export interface ServiceNode {
  node_id: string;
  queue_id: number;
  is_busy: boolean;
  current_car_id?: number;
  service_rate: number;
  total_served: number;
  total_service_time: number;
}

export interface SimulationState {
  simulation_id: string;
  status: string;
  current_time: number;
  cars: Car[];
  service_nodes: ServiceNode[];
  statistics: any;
}

// API functions
export const api = {
  // Start a new simulation
  startSimulation: async (request: SimulationRequest): Promise<{ simulation_id: string; status: string; websocket_url: string; message: string }> => {
    const response = await fetch(`${API_BASE_URL}/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to start simulation: ${response.statusText}`);
    }

    return response.json();
  },

  // Get simulation status
  getSimulationStatus: async (simulationId: string): Promise<SimulationStatus> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/status`);

    if (!response.ok) {
      throw new Error(`Failed to get simulation status: ${response.statusText}`);
    }

    return response.json();
  },

  // Get simulation state for visualization
  getSimulationState: async (simulationId: string): Promise<SimulationState> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/state`);

    if (!response.ok) {
      throw new Error(`Failed to get simulation state: ${response.statusText}`);
    }

    return response.json();
  },

  // Add a car to the simulation
  addCar: async (simulationId: string, phoneConfig?: PhoneConfig): Promise<{ car_id: number; queue_id: number; message: string }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/add_car`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(phoneConfig || {}),
    });

    if (!response.ok) {
      throw new Error(`Failed to add car: ${response.statusText}`);
    }

    return response.json();
  },

  // Update service node configuration
  updateServiceNode: async (
    simulationId: string,
    nodeId: string,
    config: { service_rate: number; service_time_variation?: number }
  ): Promise<{ node_id: string; service_rate: number; service_time_variation: number; message: string }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/service_node/${nodeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to update service node: ${response.statusText}`);
    }

    return response.json();
  },

  // Advance simulation manually (for testing)
  advanceSimulation: async (simulationId: string, dt: number = 1.0): Promise<{ advanced_by: number; completed_cars: number; current_time: number }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/advance?dt=${dt}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to advance simulation: ${response.statusText}`);
    }

    return response.json();
  },

  // Cancel simulation
  cancelSimulation: async (simulationId: string): Promise<{ simulation_id: string; status: string }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to cancel simulation: ${response.statusText}`);
    }

    return response.json();
  },

  // Update simulation time speed
  updateTimeSpeed: async (simulationId: string, timeFactor: number): Promise<{ status: string; time_factor: number }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/time_speed`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_factor: timeFactor }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update time speed: ${response.statusText}`);
    }

    return response.json();
  },

  // Add service station
  addServiceStation: async (
    simulationId: string,
    config: { queue_id: number; service_rate?: number; service_time_variation?: number }
  ): Promise<{ station_id: string; queue_id: number; service_rate: number; service_time_variation: number }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/add_station`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to add service station: ${response.statusText}`);
    }

    return response.json();
  },

  // Remove service station
  removeServiceNode: async (simulationId: string, nodeId: string): Promise<{ node_id: string; message: string }> => {
    const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/service_node/${nodeId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to remove service node: ${response.statusText}`);
    }

    return response.json();
  },

  // Get available border crossings
  getBorderCrossings: async (): Promise<{ crossings: BorderCrossing[] }> => {
    const response = await fetch(`${API_BASE_URL}/border-crossings`);

    if (!response.ok) {
      throw new Error(`Failed to get border crossings: ${response.statusText}`);
    }

    return response.json();
  },

  // WebSocket URL
  WS_BASE_URL,
};