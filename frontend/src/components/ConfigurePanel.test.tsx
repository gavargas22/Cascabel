import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfigurePanel from './ConfigurePanel';

test('renders configure panel with border config form', () => {
  render(<ConfigurePanel />);
  expect(screen.getByText('Border Crossing Configuration')).toBeInTheDocument();
  expect(screen.getByText('Simulation Configuration')).toBeInTheDocument();
});

test('updates border config num queues', () => {
  render(<ConfigurePanel />);
  const input = screen.getByDisplayValue('3');
  fireEvent.change(input, { target: { value: '4' } });
  expect(screen.getByDisplayValue('4')).toBeInTheDocument();
});

test('updates simulation config max time', () => {
  render(<ConfigurePanel />);
  const input = screen.getByDisplayValue('3600');
  fireEvent.change(input, { target: { value: '7200' } });
  expect(screen.getByDisplayValue('7200')).toBeInTheDocument();
});

test('toggles telemetry checkbox', () => {
  render(<ConfigurePanel />);
  const checkbox = screen.getByLabelText('Enable Telemetry');
  expect(checkbox).toBeChecked();
  fireEvent.click(checkbox);
  expect(checkbox).not.toBeChecked();
});