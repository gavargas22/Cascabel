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
import RealtimeMapView from './components/RealtimeMapView';
import { Card, H1, Alert, Spinner, Callout, H2 } from '@blueprintjs/core';
import './App.css';

function App() {
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [simulationState, setSimulationState] = useState<SimulationState | null>(null);
  const [simulationStatus, setSimulationStatus] = useState<SimulationStatus | null>(null);
  const [selectedCarId, setSelectedCarId] = useState<number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [timeSpeed, setTimeSpeed] = useState<number>(1.0);

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

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (simulationId) {
      const ws = new WebSocket(`ws://localhost:8001/ws/${simulationId}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnection(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'simulation_update') {
            // Update simulation status
            setSimulationStatus({
              simulation_id: data.simulation_id,
              status: data.status,
              progress: 0, // Calculate if needed
              current_time: data.current_time,
              total_arrivals: data.total_cars,
              total_completions: 0, // Not provided in WS data
              message: undefined
            });
            
            // Update simulation state
            setSimulationState({
              simulation_id: data.simulation_id,
              status: data.status,
              current_time: data.current_time,
              cars: data.cars,
              service_nodes: data.service_nodes,
              statistics: {
                throughput: 0, // Not provided
                average_wait_time: 0,
                average_service_time: 0,
                utilization: 0
              }
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
  }, [simulationId]);

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
      // State will be updated by the WebSocket connection
    } catch (err) {
      throw err; // Let ControlPanel handle the error
    }
  };

  const handleUpdateServiceNode = async (nodeId: string, rate: number) => {
    if (!simulationId) return;

    try {
      await api.updateServiceNodeRate(simulationId, nodeId, rate);
      // State will be updated by the WebSocket connection
    } catch (err) {
      throw err; // Let ControlPanel handle the error
    }
  };

  const handleCarSelect = (carId: number) => {
    setSelectedCarId(carId);
  };

  const handleAddStation = async (position: [number, number]) => {
    if (!simulationId) return;

    try {
      await api.addServiceStation(simulationId, 0); // Add to first queue for now
      // Could update local state or wait for WebSocket update
    } catch (err) {
      console.error('Failed to add station:', err);
      setError('Failed to add service station');
    }
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

            <RealtimeMapView
              cars={simulationState.cars}
              selectedCarId={selectedCarId}
              onCarSelect={handleCarSelect}
              timeSpeed={timeSpeed}
              onTimeSpeedChange={setTimeSpeed}
              onAddStation={handleAddStation}
              simulationId={simulationId}
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
