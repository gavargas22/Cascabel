import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RunPanel from './RunPanel';
import { BorderCrossingConfig, SimulationConfig } from '../services/api';

// Mock the API
jest.mock('../services/api', () => ({
  api: {
    startSimulation: jest.fn(),
    getSimulationStatus: jest.fn(),
  },
}));

const mockBorderConfig: BorderCrossingConfig = {
  num_queues: 3,
  nodes_per_queue: [2, 3, 2],
  arrival_rate: 6.0,
  service_rates: [3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9],
  queue_assignment: 'shortest',
  safe_distance: 8.0,
  max_queue_length: 50
};

const mockSimulationConfig: SimulationConfig = {
  max_simulation_time: 3600.0,
  time_factor: 1.0,
  enable_telemetry: true,
  enable_position_tracking: true
};

test('renders run panel', () => {
  render(<RunPanel borderConfig={mockBorderConfig} simulationConfig={mockSimulationConfig} />);
  expect(screen.getByText('Simulation Runner')).toBeInTheDocument();
  expect(screen.getByText('Start Simulation')).toBeInTheDocument();
});

test('starts simulation on button click', async () => {
  const mockApi = require('../services/api').api;
  mockApi.startSimulation.mockResolvedValue({
    simulation_id: 'test-id',
    status: 'running',
    websocket_url: 'ws://localhost:8000/ws/test-id',
    message: 'Started'
  });

  render(<RunPanel borderConfig={mockBorderConfig} simulationConfig={mockSimulationConfig} />);

  const button = screen.getByText('Start Simulation');
  fireEvent.click(button);

  await waitFor(() => {
    expect(mockApi.startSimulation).toHaveBeenCalledWith({
      border_config: mockBorderConfig,
      simulation_config: mockSimulationConfig,
      phone_config: undefined
    });
  });

  expect(screen.getByText('Simulation ID: test-id')).toBeInTheDocument();
});