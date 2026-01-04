import React, { useEffect, useState } from 'react';
import Map, { Marker, Source, Layer, NavigationControl } from 'react-map-gl';
import {
  Card,
  Button,
  FormGroup,
  NumericInput,
  HTMLSelect,
  Collapse,
  Tag,
  Callout,
} from '@blueprintjs/core';
import 'mapbox-gl/dist/mapbox-gl.css';
import { api, BorderCrossingConfig, SimulationConfig, PhysicsConfig } from '../services/api';

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
      path?: any;  // GeoJSON Feature with car's unique path
    }>;
    queues: Array<{
      length: number;
      throughput: number;
    }>;
    metrics: {
      total_arrivals: number;
      total_completions: number;
      average_wait_time?: number | null;
      simulation_time?: number;
    };
    traffic_control_points?: Array<{
      type: string;
      name: string;
      description: string;
      position_meters: number;
      coordinates: [number, number];
    }>;
    service_nodes?: Array<{
      node_id: string;
      queue_id: number;
      is_busy: boolean;
      current_car_id?: number;
      service_rate: number;
      total_served: number;
      total_service_time: number;
    }>;
  };
}

// Available crossings with directions
const CROSSINGS = [
  { id: 'paso_del_norte', name: 'Paso del Norte (PDN)', center: [-106.4867, 31.7508] },
  { id: 'bridge_of_the_americas', name: 'Bridge of the Americas (BOTA)', center: [-106.4519, 31.7641] },
];

const DIRECTIONS = [
  { value: 'mx2usa', label: 'Mexico → USA (Northbound)' },
  { value: 'usa2mx', label: 'USA → Mexico (Southbound)' },
];

const FullscreenDashboard: React.FC = () => {
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [simulationData, setSimulationData] = useState<SimulationUpdate['data'] | null>(null);
  const [selectedCarId, setSelectedCarId] = useState<string | null>(null);
  const [queueGeometry, setQueueGeometry] = useState<any>(null);

  // Crossing and direction selection
  const [selectedCrossing, setSelectedCrossing] = useState('paso_del_norte');
  const [selectedDirection, setSelectedDirection] = useState('mx2usa');

  // Panel visibility states
  const [showConfig, setShowConfig] = useState(true);
  const [showMetrics, setShowMetrics] = useState(true);
  const [showPaths, setShowPaths] = useState(true);  // Toggle path visibility

  // Configuration states
  const [borderConfig, setBorderConfig] = useState<BorderCrossingConfig>({
    num_queues: 2,
    nodes_per_queue: [1, 1],
    arrival_rate: 6.0,
    service_rates: [0.25, 0.25],
    queue_assignment: 'shortest',
    safe_distance: 10.0,
    max_queue_length: 50,
  });

  const [simulationConfig, setSimulationConfig] = useState<SimulationConfig>({
    max_simulation_time: 1800.0,
    time_factor: 1.0,
    enable_telemetry: true,
    enable_position_tracking: true,
  });

  const [physicsConfig] = useState<PhysicsConfig>({
    min_speed_mps: 12.1,
    max_speed_mps: 14.7,
    safe_distance_meters: 3.0,
    max_acceleration: 0.75,
    max_deceleration: 1.25,
  });

  const [isRunning, setIsRunning] = useState(false);

  // Service time range
  const [serviceTimeMin, setServiceTimeMin] = useState(3);
  const [serviceTimeMax, setServiceTimeMax] = useState(6);

  // Helper functions
  const formatSimTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const hours = Math.floor(mins / 60);
    const remainMins = mins % 60;

    if (hours > 0) {
      return `${hours}:${remainMins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

  // Load queue geometry when crossing changes
  useEffect(() => {
    const loadQueueGeometry = async () => {
      try {
        const response = await fetch('/cascabel/paths/bounding_boxes.json');
        const data = await response.json();
        const geometry = data[selectedCrossing]?.preferred_queue_geometry;
        setQueueGeometry(geometry);
        console.log('Queue geometry loaded:', geometry);
      } catch (error) {
        console.error('Failed to load queue geometry:', error);
      }
    };

    loadQueueGeometry();
  }, [selectedCrossing]);

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
          console.log('Received simulation update:', {
            carCount: message.data.cars.length,
            firstCar: message.data.cars[0],
            queues: message.data.queues.length
          });
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
      const generateServiceRates = (numNodes: number) => {
        return Array.from({ length: numNodes }, () => {
          const range = serviceTimeMax - serviceTimeMin;
          const serviceTimeMinutes = serviceTimeMin + Math.random() * range;
          return 1 / serviceTimeMinutes;
        });
      };

      const totalNodes = borderConfig.nodes_per_queue.reduce((sum, n) => sum + n, 0);
      const serviceRatesWithVariation = generateServiceRates(totalNodes);

      const response = await api.startSimulation({
        crossing_name: selectedCrossing,
        direction: selectedDirection,
        border_config: {
          ...borderConfig,
          service_rates: serviceRatesWithVariation,
        },
        simulation_config: simulationConfig,
        phone_config: {
          sampling_rate: 10.0,
          gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 10.0 },
          accelerometer_noise: 0.1,
          gyro_noise: 0.01,
          device_orientation: 'portrait',
        },
        physics_config: physicsConfig,
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
      try {
        const response = await fetch(`${API_BASE_URL}/simulation/${simulationId}/stop`, {
          method: 'POST',
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Simulation stopped:', result);
          alert(`Simulation stopped!\n${result.message}`);
        }
      } catch (error) {
        console.error('Error stopping simulation:', error);
      } finally {
        ws.close();
        setSimulationId(null);
        setSimulationData(null);
        setIsRunning(false);
      }
    }
  };

  // Get map center based on selected crossing
  const mapCenter = CROSSINGS.find(c => c.id === selectedCrossing)?.center || [-106.4867, 31.7508];

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {/* Fullscreen Map */}
      <Map
        initialViewState={{
          longitude: mapCenter[0],
          latitude: mapCenter[1],
          zoom: 15,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/gavargas/ck1yptdx72uqd1cn0x144h6sx"
        mapboxAccessToken={process.env.REACT_APP_MAPBOX_TOKEN}
      >
        {/* Individual Car Paths */}
        {showPaths && simulationData?.cars.map((car) => {
          if (!car.path) return null;

          const isSelected = selectedCarId === car.id;
          const carColor = getCarColor(car.status);

          return (
            <Source key={`car-path-${car.id}`} id={`car-path-${car.id}`} type="geojson" data={car.path}>
              <Layer
                id={`car-path-line-${car.id}`}
                type="line"
                paint={{
                  'line-color': isSelected ? carColor : '#888888',
                  'line-width': isSelected ? 3 : 1.5,
                  'line-opacity': isSelected ? 0.8 : 0.15,
                }}
              />
            </Source>
          );
        })}

        {/* Queue Geometry Layer (preferred_queue_geometry) - Semi-transparent */}
        {queueGeometry && showPaths && (
          <Source id="queue-path" type="geojson" data={queueGeometry}>
            <Layer
              id="queue-path-line"
              type="line"
              paint={{
                'line-color': '#ff6b6b',
                'line-width': 3,
                'line-opacity': 0.4,  // Semi-transparent
              }}
            />
            <Layer
              id="queue-path-outline"
              type="line"
              paint={{
                'line-color': '#c92a2a',
                'line-width': 5,
                'line-opacity': 0.2,  // Very transparent outline
              }}
            />
          </Source>
        )}

        {/* Car Markers */}
        {simulationData?.cars.map((car) => (
          <Marker
            key={car.id}
            longitude={car.position[0]}
            latitude={car.position[1]}
            anchor="center"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              setSelectedCarId(car.id);
              console.log('Selected car:', car);
            }}
          >
            <div
              style={{
                width: selectedCarId === car.id ? '24px' : '16px',
                height: selectedCarId === car.id ? '24px' : '16px',
                borderRadius: '50%',
                backgroundColor: getCarColor(car.status),
                border: selectedCarId === car.id ? '3px solid #ffffff' : '2px solid #ffffff',
                boxShadow: '0 3px 10px rgba(0,0,0,0.6)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                zIndex: selectedCarId === car.id ? 1000 : 500,
              }}
              title={`Car ${car.id} - ${car.status} - ${car.velocity?.toFixed(1)} m/s`}
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
              <>
                <Tag intent="success" large style={{ marginBottom: '10px', width: '100%' }}>
                  ● RUNNING - ID: {simulationId?.substring(0, 8)}...
                </Tag>
                {simulationData && (
                  <div style={{ fontSize: '11px', marginBottom: '10px', textAlign: 'center' }}>
                    {simulationData.cars.length === 0 ? (
                      <span style={{ color: '#9e6a03' }}>
                        ⏳ Waiting for cars to arrive... ({borderConfig.arrival_rate} cars/min)
                      </span>
                    ) : (
                      <span style={{ color: '#0f9960' }}>
                        🚗 {simulationData.cars.length} car{simulationData.cars.length !== 1 ? 's' : ''} on map
                      </span>
                    )}
                  </div>
                )}
              </>
            )}

            <FormGroup label="Border Crossing" style={{ marginBottom: '10px' }}>
              <HTMLSelect
                value={selectedCrossing}
                onChange={(e) => setSelectedCrossing(e.currentTarget.value)}
                disabled={isRunning}
                style={{ width: '100%' }}
              >
                {CROSSINGS.map((crossing) => (
                  <option key={crossing.id} value={crossing.id}>
                    {crossing.name}
                  </option>
                ))}
              </HTMLSelect>
            </FormGroup>

            <FormGroup label="Traffic Direction" style={{ marginBottom: '10px' }}>
              <HTMLSelect
                value={selectedDirection}
                onChange={(e) => setSelectedDirection(e.currentTarget.value)}
                disabled={isRunning}
                style={{ width: '100%' }}
              >
                {DIRECTIONS.map((dir) => (
                  <option key={dir.value} value={dir.value}>
                    {dir.label}
                  </option>
                ))}
              </HTMLSelect>
            </FormGroup>

            <FormGroup label="Queues" inline>
              <NumericInput
                value={borderConfig.num_queues}
                onValueChange={(val) => {
                  const newNodesPerQueue = Array(val).fill(1);
                  const totalNodes = val;
                  const newServiceRates = Array(totalNodes).fill(0.25);

                  setBorderConfig({
                    ...borderConfig,
                    num_queues: val,
                    nodes_per_queue: newNodesPerQueue,
                    service_rates: newServiceRates,
                  });
                }}
                min={1}
                max={20}
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

            <FormGroup label="Service Time Range (min)" inline>
              <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
                <NumericInput
                  value={serviceTimeMin}
                  onValueChange={(val) => setServiceTimeMin(Math.min(val, serviceTimeMax - 0.5))}
                  min={1}
                  max={15}
                  stepSize={0.5}
                  style={{ width: '60px' }}
                  disabled={isRunning}
                />
                <span>-</span>
                <NumericInput
                  value={serviceTimeMax}
                  onValueChange={(val) => setServiceTimeMax(Math.max(val, serviceTimeMin + 0.5))}
                  min={1}
                  max={15}
                  stepSize={0.5}
                  style={{ width: '60px' }}
                  disabled={isRunning}
                />
              </div>
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

            <div style={{ marginTop: '10px' }}>
              <Button
                minimal
                small
                icon={showPaths ? 'eye-open' : 'eye-off'}
                onClick={() => setShowPaths(!showPaths)}
              >
                {showPaths ? 'Hide' : 'Show'} Queue Path
              </Button>
            </div>

            <div style={{ marginTop: '10px', padding: '8px', backgroundColor: '#e8f4f8', borderRadius: '4px', fontSize: '11px', color: '#5c7080' }}>
              <strong>ℹ️ New System:</strong> Cars spawn in {selectedDirection === 'mx2usa' ? 'Mexico' : 'USA'},
              take unique paths, and join the queue at the border.
            </div>
          </Collapse>
        </Card>
      </div>

      {/* Floating Metrics Panel - Top Right */}
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
                {simulationData.metrics.simulation_time !== undefined && (
                  <div style={{ marginBottom: '12px', padding: '10px', backgroundColor: '#e8f4f8', borderRadius: '4px', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#5c7080', marginBottom: '4px' }}>
                      Simulation Time
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#106ba3', fontFamily: 'monospace' }}>
                      {formatSimTime(simulationData.metrics.simulation_time)}
                    </div>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Total Arrivals:</strong>
                  <span>{simulationData.metrics.total_arrivals}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Total Completions:</strong>
                  <span>{simulationData.metrics.total_completions}</span>
                </div>
                <div style={{ marginTop: '12px', padding: '10px', backgroundColor: '#f0f8ff', borderRadius: '4px' }}>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                    Average Wait Time
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#007bff' }}>
                    {simulationData.metrics.average_wait_time !== null && simulationData.metrics.average_wait_time !== undefined
                      ? `${simulationData.metrics.average_wait_time.toFixed(1)}s`
                      : '—'}
                  </div>
                  {simulationData.metrics.average_wait_time !== null && simulationData.metrics.average_wait_time !== undefined && (
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      ({(simulationData.metrics.average_wait_time / 60).toFixed(2)} min)
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <Callout intent="warning" icon="info-sign">
                Start a simulation to see metrics
              </Callout>
            )}
          </Collapse>
        </Card>
      </div>

      {/* Compact Car Info Panel - Bottom Right */}
      {selectedCarId && simulationData && (
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            right: '20px',
            width: '280px',
            zIndex: 1000,
          }}
        >
          <Card
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              padding: '12px',
            }}
          >
            {(() => {
              const car = simulationData.cars.find(c => c.id === selectedCarId);
              if (!car) return null;

              return (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '14px' }}>Car {car.id}</h4>
                    <Button
                      minimal
                      small
                      icon="cross"
                      onClick={() => setSelectedCarId(null)}
                    />
                  </div>
                  <div style={{ fontSize: '12px', lineHeight: '1.6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <strong>Status:</strong>
                      <Tag
                        minimal
                        style={{
                          backgroundColor: getCarColor(car.status),
                          color: 'white',
                          fontSize: '10px',
                          padding: '2px 6px'
                        }}
                      >
                        {car.status.toUpperCase()}
                      </Tag>
                    </div>
                    {car.velocity !== undefined && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>Speed:</strong>
                        <span>{car.velocity.toFixed(2)} m/s ({(car.velocity * 3.6).toFixed(1)} km/h)</span>
                      </div>
                    )}
                    {car.acceleration !== undefined && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>Acceleration:</strong>
                        <span>{car.acceleration.toFixed(3)} m/s²</span>
                      </div>
                    )}
                    {car.queue_id !== undefined && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>Queue:</strong>
                        <span>#{car.queue_id}</span>
                      </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e0e0e0' }}>
                      <strong>Position:</strong>
                      <span style={{ fontSize: '10px', fontFamily: 'monospace' }}>
                        {car.position[1].toFixed(5)}, {car.position[0].toFixed(5)}
                      </span>
                    </div>
                  </div>
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
          <div style={{ display: 'flex', gap: '15px', fontSize: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
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
              <div style={{ width: '4px', height: '15px', backgroundColor: '#ff6b6b', opacity: 0.4 }} />
              <span>Queue Zone</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '4px', height: '15px', backgroundColor: '#888888', opacity: 0.3 }} />
              <span>Car Paths</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default FullscreenDashboard;
