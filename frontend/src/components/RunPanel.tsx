import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  H3,
  ProgressBar,
  Callout,
  Spinner,
  Text,
  Divider
} from '@blueprintjs/core';
import { api, BorderCrossingConfig, SimulationConfig, PhoneConfig, SimulationStatus } from '../services/api';

interface RunPanelProps {
  borderConfig: BorderCrossingConfig;
  simulationConfig: SimulationConfig;
  phoneConfig?: PhoneConfig;
  onSimulationStart?: (id: string) => void;
  onViewMap?: () => void;
}

const RunPanel: React.FC<RunPanelProps> = ({ borderConfig, simulationConfig, phoneConfig, onSimulationStart, onViewMap }) => {
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  const startSimulation = async () => {
    setIsStarting(true);
    setError(null);
    try {
      const request = {
        border_config: borderConfig,
        simulation_config: simulationConfig,
        phone_config: phoneConfig
      };
      const response = await api.startSimulation(request);
      setSimulationId(response.simulation_id);
      onSimulationStart?.(response.simulation_id);
      setStatus({
        simulation_id: response.simulation_id,
        status: 'running',
        progress: 0,
        current_time: 0,
        total_arrivals: 0,
        total_completions: 0
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start simulation');
    } finally {
      setIsStarting(false);
    }
  };

  const cancelSimulation = async () => {
    if (!simulationId) return;
    try {
      await fetch(`${api.WS_BASE_URL.replace('ws', 'http')}/simulation/${simulationId}`, { method: 'DELETE' });
      setStatus(prev => prev ? { ...prev, status: 'cancelled' } : null);
      setSimulationId(null);
    } catch (err) {
      setError('Failed to cancel simulation');
    }
  };

  useEffect(() => {
    if (simulationId && status?.status === 'running') {
      const ws = new WebSocket(`${api.WS_BASE_URL}/ws/${simulationId}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'simulation_update') {
            setStatus({
              simulation_id: data.simulation_id,
              status: data.status,
              progress: data.current_time / simulationConfig.max_simulation_time,
              current_time: data.current_time,
              total_arrivals: data.total_cars,
              total_completions: 0, // Not provided in WS data
            });
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnection(null);
      };

      return () => {
        ws.close();
      };
    }
  }, [simulationId, status?.status, simulationConfig.max_simulation_time]);

  useEffect(() => {
    if (simulationId && status?.status === 'running') {
      const interval = setInterval(async () => {
        try {
          const updatedStatus = await api.getSimulationStatus(simulationId);
          setStatus(updatedStatus);
          if (updatedStatus.status !== 'running') {
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Failed to get status:', err);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [simulationId, status?.status]);

  return (
    <div>
      <Card>
        <H3>Simulation Runner</H3>
        {!simulationId ? (
          <div>
            <Text>Ready to start simulation with current configuration.</Text>
            <br />
            <Button
              intent="primary"
              onClick={startSimulation}
              loading={isStarting}
              large
            >
              Start Simulation
            </Button>
          </div>
        ) : (
          <div>
            <Text>Simulation ID: {simulationId}</Text>
            <br />
            <Text>Status: {status?.status}</Text>
            <br />
            <ProgressBar value={status?.progress || 0} />
            <br />
            <Text>Current Time: {status?.current_time?.toFixed(1)}s</Text>
            <br />
            <Text>Total Arrivals: {status?.total_arrivals}</Text>
            <br />
            <Text>Total Completions: {status?.total_completions}</Text>
            <br />
            {status?.status === 'running' && (
              <>
                <Button intent="primary" onClick={onViewMap} style={{ marginRight: '10px' }}>
                  View Map
                </Button>
                <Button intent="danger" onClick={cancelSimulation}>
                  Cancel Simulation
                </Button>
              </>
            )}
            {status?.status === 'completed' && (
              <Callout intent="success" title="Simulation Completed">
                The simulation has finished successfully.
              </Callout>
            )}
            {status?.status === 'failed' && (
              <Callout intent="danger" title="Simulation Failed">
                {status.message || 'An error occurred during simulation.'}
              </Callout>
            )}
          </div>
        )}
      </Card>

      {error && (
        <Callout intent="danger" title="Error">
          {error}
        </Callout>
      )}

      <Divider />

      <Card>
        <H3>Real-time Updates</H3>
        {wsConnection ? (
          <Callout intent="success">
            Connected to real-time updates
          </Callout>
        ) : simulationId ? (
          <Callout intent="warning">
            Connecting to real-time updates...
          </Callout>
        ) : (
          <Text>No active simulation</Text>
        )}
      </Card>
    </div>
  );
};

export default RunPanel;