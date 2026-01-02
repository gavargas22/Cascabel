import React, { useEffect, useState, useRef } from 'react';
import Map, { Marker, Source, Layer, NavigationControl } from 'react-map-gl';
import {
  Card,
  Button,
  FormGroup,
  NumericInput,
  HTMLSelect,
  Collapse,
  Icon,
  Tag,
  Callout,
} from '@blueprintjs/core';
import 'mapbox-gl/dist/mapbox-gl.css';
import { api, BorderCrossingConfig, SimulationConfig, PhoneConfig } from '../services/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface SimulationUpdate {
  type: 'simulation_update';
  data: {
    cars: Array<{
      id: string;
      position: [number, number];
      status: string;
      velocity?: number;
      acceleration?: number;
      queue_id?: number;
    }>;
    queues: Array<{
      length: number;
      throughput: number;
    }>;
    metrics: {
      total_arrivals: number;
      total_completions: number;
      average_wait_time?: number | null;
    };
  };
}

const FullscreenDashboard: React.FC = () => {
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [simulationData, setSimulationData] = useState<SimulationUpdate['data'] | null>(null);
  const [selectedCarId, setSelectedCarId] = useState<string | null>(null);
  const [geojsonData, setGeojsonData] = useState<any>(null);

  // Panel visibility states
  const [showConfig, setShowConfig] = useState(true);
  const [showMetrics, setShowMetrics] = useState(true);
  const [showCarList, setShowCarList] = useState(false);

  // Configuration states
  const [borderConfig, setBorderConfig] = useState<BorderCrossingConfig>({
    num_queues: 2,
    nodes_per_queue: [1, 1],
    arrival_rate: 10.0,
    service_rates: [3.0, 3.0],
    queue_assignment: 'shortest',
    safe_distance: 10.0,
    max_queue_length: 50,
  });

  const [simulationConfig, setSimulationConfig] = useState<SimulationConfig>({
    max_simulation_time: 1800.0,
    time_factor: 10.0,
    enable_telemetry: true,
    enable_position_tracking: true,
  });

  const [isRunning, setIsRunning] = useState(false);

  // Load GeoJSON boundary data
  useEffect(() => {
    fetch(`${API_BASE_URL}/geojson/usa2mx/bota`)
      .then((res) => res.json())
      .then((data) => {
        console.log('GeoJSON loaded:', data);
        setGeojsonData(data);
      })
      .catch((err) => console.error('Failed to load GeoJSON:', err));
  }, []);

  // WebSocket connection
  useEffect(() => {
    if (!simulationId) return;

    const websocket = new WebSocket(`${api.WS_BASE_URL}/ws/${simulationId}`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsRunning(true);
    };

    websocket.onmessage = (event) => {
      try {
        const message: SimulationUpdate = JSON.parse(event.data);
        if (message.type === 'simulation_update') {
          console.log('Simulation update:', message.data);
          setSimulationData(message.data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsRunning(false);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [simulationId]);

  const handleStartSimulation = async () => {
    try {
      const response = await api.startSimulation({
        border_config: borderConfig,
        simulation_config: simulationConfig,
        phone_config: {
          sampling_rate: 10.0,
          gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 10.0 },
          accelerometer_noise: 0.1,
          gyro_noise: 0.01,
          device_orientation: 'portrait',
        },
      });
      setSimulationId(response.simulation_id);
      console.log('Simulation started:', response.simulation_id);
    } catch (error) {
      console.error('Failed to start simulation:', error);
      alert('Failed to start simulation: ' + error);
    }
  };

  const handleStopSimulation = async () => {
    if (simulationId && ws) {
      ws.close();
      setSimulationId(null);
      setSimulationData(null);
      setIsRunning(false);
    }
  };

  const getCarColor = (status: string) => {
    switch (status) {
      case 'approaching':
      case 'arriving':
        return '#007bff';
      case 'queued':
        return '#ffc107';
      case 'serving':
        return '#28a745';
      case 'completed':
        return '#dc3545';
      default:
        return '#6c757d';
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {/* Fullscreen Map */}
      <Map
        initialViewState={{
          longitude: -106.4519, // Center of the GeoJSON path
          latitude: 31.7641,
          zoom: 15,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/gavargas/ck1yptdx72uqd1cn0x144h6sx"
        mapboxAccessToken={process.env.REACT_APP_MAPBOX_TOKEN}
      >
        {/* GeoJSON Path Layer */}
        {geojsonData && (
          <>
            <Source id="border-path" type="geojson" data={geojsonData}>
              <Layer
                id="border-path-line"
                type="line"
                paint={{
                  'line-color': '#ff0000',
                  'line-width': 4,
                  'line-opacity': 0.8,
                }}
              />
            </Source>
          </>
        )}

        {/* Car Markers */}
        {simulationData?.cars.map((car) => (
          <Marker
            key={car.id}
            longitude={car.position[0]}
            latitude={car.position[1]}
            anchor="center"
            onClick={() => setSelectedCarId(car.id)}
          >
            <div
              style={{
                width: selectedCarId === car.id ? '20px' : '14px',
                height: selectedCarId === car.id ? '20px' : '14px',
                borderRadius: '50%',
                backgroundColor: getCarColor(car.status),
                border: selectedCarId === car.id ? '3px solid #ffffff' : '2px solid #ffffff',
                boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              title={`Car ${car.id} - ${car.status}`}
            />
          </Marker>
        ))}

        <NavigationControl position="top-right" />
      </Map>

      {/* Floating Control Panel - Top Left */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          maxWidth: '380px',
          zIndex: 1000,
        }}
      >
        <Card
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: 0 }}>🚗 Simulation Control</h3>
            <Button
              minimal
              small
              icon={showConfig ? 'chevron-up' : 'chevron-down'}
              onClick={() => setShowConfig(!showConfig)}
            />
          </div>

          <Collapse isOpen={showConfig}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <Button
                intent="success"
                icon="play"
                onClick={handleStartSimulation}
                disabled={isRunning}
                style={{ flex: 1 }}
              >
                Start
              </Button>
              <Button
                intent="danger"
                icon="stop"
                onClick={handleStopSimulation}
                disabled={!isRunning}
                style={{ flex: 1 }}
              >
                Stop
              </Button>
            </div>

            {isRunning && (
              <Tag intent="success" large style={{ marginBottom: '10px', width: '100%' }}>
                ● RUNNING - ID: {simulationId?.substring(0, 8)}...
              </Tag>
            )}

            <FormGroup label="Queues" inline>
              <NumericInput
                value={borderConfig.num_queues}
                onValueChange={(val) =>
                  setBorderConfig({ ...borderConfig, num_queues: val })
                }
                min={1}
                max={5}
                style={{ width: '80px' }}
                disabled={isRunning}
              />
            </FormGroup>

            <FormGroup label="Arrival Rate (cars/min)" inline>
              <NumericInput
                value={borderConfig.arrival_rate}
                onValueChange={(val) =>
                  setBorderConfig({ ...borderConfig, arrival_rate: val })
                }
                min={1}
                max={20}
                stepSize={0.5}
                style={{ width: '80px' }}
                disabled={isRunning}
              />
            </FormGroup>

            <FormGroup label="Time Factor (speed)" inline>
              <NumericInput
                value={simulationConfig.time_factor}
                onValueChange={(val) =>
                  setSimulationConfig({ ...simulationConfig, time_factor: val })
                }
                min={1}
                max={60}
                stepSize={1}
                style={{ width: '80px' }}
                disabled={isRunning}
              />
            </FormGroup>

            <FormGroup label="Queue Assignment" inline>
              <HTMLSelect
                value={borderConfig.queue_assignment}
                onChange={(e) =>
                  setBorderConfig({
                    ...borderConfig,
                    queue_assignment: e.target.value as any,
                  })
                }
                disabled={isRunning}
                style={{ width: '150px' }}
              >
                <option value="shortest">Shortest</option>
                <option value="random">Random</option>
                <option value="round_robin">Round Robin</option>
              </HTMLSelect>
            </FormGroup>
          </Collapse>
        </Card>
      </div>

      {/* Floating Metrics Panel - Top Right (below nav controls) */}
      <div
        style={{
          position: 'absolute',
          top: '120px',
          right: '20px',
          width: '300px',
          zIndex: 1000,
        }}
      >
        <Card
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: 0 }}>📊 Live Metrics</h3>
            <Button
              minimal
              small
              icon={showMetrics ? 'chevron-up' : 'chevron-down'}
              onClick={() => setShowMetrics(!showMetrics)}
            />
          </div>

          <Collapse isOpen={showMetrics}>
            {simulationData ? (
              <div style={{ fontSize: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Cars on Map:</strong>
                  <Tag intent="primary">{simulationData.cars.length}</Tag>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Queue Length:</strong>
                  <Tag>{simulationData.queues.reduce((sum, q) => sum + q.length, 0)}</Tag>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Active Booths:</strong>
                  <Tag intent="success">
                    {simulationData.queues.reduce((sum, q) => sum + q.throughput, 0)}
                  </Tag>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Total Arrivals:</strong>
                  <span>{simulationData.metrics.total_arrivals}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Total Completions:</strong>
                  <span>{simulationData.metrics.total_completions}</span>
                </div>
                {simulationData.metrics.average_wait_time !== null &&
                  simulationData.metrics.average_wait_time !== undefined && (
                    <div style={{ marginTop: '12px', padding: '10px', backgroundColor: '#f0f8ff', borderRadius: '4px' }}>
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                        Average Wait Time
                      </div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#007bff' }}>
                        {simulationData.metrics.average_wait_time.toFixed(1)}s
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        ({(simulationData.metrics.average_wait_time / 60).toFixed(2)} min)
                      </div>
                    </div>
                  )}
              </div>
            ) : (
              <Callout intent="warning" icon="info-sign">
                Start a simulation to see metrics
              </Callout>
            )}
          </Collapse>
        </Card>
      </div>

      {/* Floating Car List Panel - Bottom Right */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          width: '300px',
          maxHeight: '400px',
          zIndex: 1000,
        }}
      >
        <Card
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: 0 }}>
              🚙 Cars ({simulationData?.cars.length || 0})
            </h3>
            <Button
              minimal
              small
              icon={showCarList ? 'chevron-down' : 'chevron-up'}
              onClick={() => setShowCarList(!showCarList)}
            />
          </div>

          <Collapse isOpen={showCarList}>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {simulationData?.cars.length === 0 ? (
                <Callout intent="none" icon="endorsed">
                  No active cars
                  {simulationData.metrics.total_completions > 0 &&
                    ` (${simulationData.metrics.total_completions} completed)`}
                </Callout>
              ) : (
                simulationData?.cars.map((car) => (
                  <div
                    key={car.id}
                    onClick={() => setSelectedCarId(car.id)}
                    style={{
                      padding: '8px',
                      marginBottom: '6px',
                      backgroundColor:
                        selectedCarId === car.id ? '#e1f5fe' : '#f8f9fa',
                      border:
                        selectedCarId === car.id
                          ? '2px solid #2196f3'
                          : '1px solid #dee2e6',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Car {car.id}</span>
                      <div
                        style={{
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: getCarColor(car.status),
                          marginTop: '4px'
                        }}
                      />
                    </div>
                    <div style={{ fontSize: '11px', color: '#666' }}>
                      <div>{car.status}</div>
                      {car.velocity !== undefined && (
                        <div>{car.velocity.toFixed(1)} m/s</div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Collapse>
        </Card>
      </div>

      {/* Selected Car Details - Bottom Left */}
      {selectedCarId && simulationData && (
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            width: '280px',
            zIndex: 1000,
          }}
        >
          <Card
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h3 style={{ margin: 0 }}>Car {selectedCarId}</h3>
              <Button
                minimal
                small
                icon="cross"
                onClick={() => setSelectedCarId(null)}
              />
            </div>
            {(() => {
              const car = simulationData.cars.find((c) => c.id === selectedCarId);
              if (!car) return <div>Car not found</div>;
              return (
                <div style={{ fontSize: '13px' }}>
                  <div style={{ marginBottom: '6px' }}>
                    <strong>Status:</strong>{' '}
                    <Tag
                      style={{
                        backgroundColor: getCarColor(car.status),
                        color: 'white',
                      }}
                    >
                      {car.status}
                    </Tag>
                  </div>
                  <div style={{ marginBottom: '6px' }}>
                    <strong>Position:</strong> [{car.position[1].toFixed(6)},{' '}
                    {car.position[0].toFixed(6)}]
                  </div>
                  {car.velocity !== undefined && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Velocity:</strong> {car.velocity.toFixed(2)} m/s
                    </div>
                  )}
                  {car.acceleration !== undefined && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Acceleration:</strong> {car.acceleration.toFixed(2)} m/s²
                    </div>
                  )}
                  {car.queue_id !== undefined && car.queue_id !== null && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Queue:</strong> {car.queue_id}
                    </div>
                  )}
                </div>
              );
            })()}
          </Card>
        </div>
      )}

      {/* Legend - Bottom Center */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
        }}
      >
        <Card
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            padding: '10px 20px',
          }}
        >
          <div style={{ display: 'flex', gap: '15px', fontSize: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#007bff' }} />
              <span>Arriving</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ffc107' }} />
              <span>Queued</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#28a745' }} />
              <span>Serving</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '4px', height: '15px', backgroundColor: '#ff0000' }} />
              <span>Border Path</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default FullscreenDashboard;
