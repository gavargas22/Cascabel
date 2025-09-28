import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import ResultsPanel from './ResultsPanel';

// Mock the API
jest.mock('../services/api', () => ({
  api: {
    getSimulationStatus: jest.fn(),
  },
}));

test('renders results panel with no simulation', () => {
  render(<ResultsPanel simulationId={null} />);
  expect(screen.getByText('Simulation Results')).toBeInTheDocument();
  expect(screen.getByText('No simulation results available. Run a simulation first.')).toBeInTheDocument();
});

test('renders results panel with simulation data', async () => {
  const mockApi = require('../services/api').api;
  mockApi.getSimulationStatus.mockResolvedValue({
    simulation_id: 'test-id',
    status: 'completed',
    progress: 1.0,
    current_time: 3600,
    total_arrivals: 100,
    total_completions: 95
  });

  render(<ResultsPanel simulationId="test-id" />);

  await waitFor(() => {
    expect(screen.getByText('Simulation ID: test-id')).toBeInTheDocument();
    expect(screen.getByText('Status: completed')).toBeInTheDocument();
    expect(screen.getByText('Total Arrivals: 100')).toBeInTheDocument();
  });
});