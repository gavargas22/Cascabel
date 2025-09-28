import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders dashboard header', () => {
  render(<App />);
  const headerElement = screen.getByText(/Border Traffic Simulation Dashboard/i);
  expect(headerElement).toBeInTheDocument();
});

test('renders tabs', () => {
  render(<App />);
  expect(screen.getByText('Create')).toBeInTheDocument();
  expect(screen.getByText('Configure')).toBeInTheDocument();
  expect(screen.getByText('Run')).toBeInTheDocument();
  expect(screen.getByText('Results')).toBeInTheDocument();
});
