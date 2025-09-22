import React, { useState, useEffect } from 'react';
import {
  SimulationState,
  SimulationStatus,
  BorderCrossingConfig,
  SimulationConfig,
  PhoneConfig
} from './services/api';
import { api } from './services/api';
import QueueVisualization from './components/QueueVisualization';
import CarTelemetryDashboard from './components/CarTelemetryDashboard';
import ControlPanel from './components/ControlPanel';
import MapView from './components/MapView';
import { Card, H1, Alert, Spinner, Callout, H2 } from '@blueprintjs/core';
import './App.css';

function App() {
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [simulationState, setSimulationState] = useState<SimulationState | null>(null);
  const [simulationStatus, setSimulationStatus] = useState<SimulationStatus | null>(null);
  const [selectedCarId, setSelectedCarId] = useState<number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Default configuration
  const defaultBorderConfig: BorderCrossingConfig = {
    num_queues: 3,
    nodes_per_queue: [2, 3, 2],
    arrival_rate: 6.0,
    service_rates: [3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9],
    queue_assignment: 'shortest',
    safe_distance: 8.0,
    max_queue_length: 50
  };

  const defaultSimulationConfig: SimulationConfig = {
    max_simulation_time: 3600.0,
    time_factor: 1.0,
    enable_telemetry: true,
    enable_position_tracking: true
  };

  // Poll for simulation updates
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (simulationId && simulationStatus?.status === 'running') {
      interval = setInterval(async () => {
        try {
          const [status, state] = await Promise.all([
            api.getSimulationStatus(simulationId),
            api.getSimulationState(simulationId)
          ]);
          setSimulationStatus(status);
          setSimulationState(state);
        } catch (err) {
          console.error('Failed to update simulation:', err);
        }
      }, 1000); // Update every second
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [simulationId, simulationStatus?.status]);

  const handleStartSimulation = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const phoneConfig: PhoneConfig = {
        sampling_rate: 10,
        gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 3.0 },
        accelerometer_noise: 0.01,
        gyro_noise: 0.001,
        device_orientation: 'portrait'
      };

      const response = await api.startSimulation({
        border_config: defaultBorderConfig,
        simulation_config: defaultSimulationConfig,
        phone_config: phoneConfig
      });

      setSimulationId(response.simulation_id);

      // Get initial status
      const status = await api.getSimulationStatus(response.simulation_id);
      setSimulationStatus(status);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start simulation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopSimulation = async () => {
    if (!simulationId) return;

    try {
      await api.cancelSimulation(simulationId);
      setSimulationId(null);
      setSimulationState(null);
      setSimulationStatus(null);
      setSelectedCarId(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop simulation');
    }
  };

  const handleAddCar = async (phoneConfig?: PhoneConfig) => {
    if (!simulationId) return;

    try {
      await api.addCar(simulationId, phoneConfig);
      // State will be updated by the polling effect
    } catch (err) {
      throw err; // Let ControlPanel handle the error
    }
  };

  const handleUpdateServiceNode = async (nodeId: string, rate: number) => {
    if (!simulationId) return;

    try {
      await api.updateServiceNodeRate(simulationId, nodeId, rate);
      // State will be updated by the polling effect
    } catch (err) {
      throw err; // Let ControlPanel handle the error
    }
  };

  const handleCarSelect = (carId: number) => {
    setSelectedCarId(carId);
  };

  return (
    <div className="App">
      <Card className="App-header">
        <H1>Cascabel Border Crossing Simulation</H1>
        <p>Real-time visualization of car queue dynamics</p>
      </Card>

      <main className="App-main">
        {error && (
          <Alert
            intent="danger"
            isOpen={true}
            onClose={() => setError(null)}
          >
            <strong>Error:</strong> {error}
          </Alert>
        )}

        <ControlPanel
          simulationId={simulationId}
          serviceNodes={simulationState?.service_nodes || []}
          onAddCar={handleAddCar}
          onUpdateServiceNode={handleUpdateServiceNode}
          onStartSimulation={handleStartSimulation}
          onStopSimulation={handleStopSimulation}
          isRunning={simulationStatus?.status === 'running'}
        />

        {simulationState && (
          <>
            <QueueVisualization
              cars={simulationState.cars}
              serviceNodes={simulationState.service_nodes}
              numQueues={defaultBorderConfig.num_queues}
              selectedCarId={selectedCarId}
              onCarSelect={handleCarSelect}
            />

            <MapView
              cars={simulationState.cars}
              selectedCarId={selectedCarId}
              onCarSelect={handleCarSelect}
            />

            <CarTelemetryDashboard
              cars={simulationState.cars}
              selectedCarId={selectedCarId}
              onCarSelect={handleCarSelect}
            />

            <Card className="simulation-stats">
              <H2>Simulation Statistics</H2>
              <div className="stats-grid">
                <Callout>
                  <strong>Current Time:</strong> {simulationState.current_time.toFixed(1)}s
                </Callout>
                <Callout>
                  <strong>Total Cars:</strong> {simulationState.cars.length}
                </Callout>
                <Callout>
                  <strong>Active Service Nodes:</strong> {simulationState.service_nodes.filter(n => n.is_busy).length} / {simulationState.service_nodes.length}
                </Callout>
                <Callout>
                  <strong>Throughput:</strong> {simulationState.statistics.throughput?.toFixed(2) || '0.00'} cars/min
                </Callout>
              </div>
            </Card>
          </>
        )}

        {isLoading && (
          <Card className="loading">
            <Spinner />
            <p>Starting simulation...</p>
          </Card>
        )}
      </main>
    </div>
  );
}

export default App;
