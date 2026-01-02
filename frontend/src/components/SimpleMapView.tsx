import React, { useEffect, useState } from 'react';
import { Card, H2, Button, Switch, FormGroup } from '@blueprintjs/core';
import Map, { Marker, NavigationControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { api } from '../services/api';

interface SimpleMapViewProps {
  simulationId: string;
}

interface SimulationUpdate {
  type: 'simulation_update';
  data: {
    cars: Array<{
      id: string;
      position: [number, number]; // [longitude, latitude]
      status: 'approaching' | 'queued' | 'serving' | 'completed';
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
      average_wait_time?: number;
    };
  };
}

const SimpleMapView: React.FC<SimpleMapViewProps> = ({ simulationId }) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [simulationData, setSimulationData] = useState<SimulationUpdate['data'] | null>(null);
  const [selectedCarId, setSelectedCarId] = useState<string | null>(null);
  const [showMetrics, setShowMetrics] = useState(true);

  useEffect(() => {
    const websocket = new WebSocket(`${api.WS_BASE_URL}/ws/${simulationId}`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
      try {
        const message: SimulationUpdate = JSON.parse(event.data);
        if (message.type === 'simulation_update') {
          console.log('Received update:', message.data);
          setSimulationData(message.data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [simulationId]);

  const getCarColor = (status: string) => {
    switch (status) {
      case 'approaching':
      case 'arriving':
        return '#007bff'; // Blue
      case 'queued':
        return '#ffc107'; // Yellow
      case 'serving':
        return '#28a745'; // Green
      case 'completed':
        return '#dc3545'; // Red
      default:
        return '#6c757d'; // Gray
    }
  };

  return (
    <div style={{ display: 'flex', height: '700px', gap: '10px' }}>
      <div style={{ flex: 1 }}>
        <Card style={{ height: '100%', overflow: 'hidden' }}>
          <H2>Real-time Map View</H2>
          <p style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>
            Simulation ID: {simulationId}
          </p>

          {!process.env.REACT_APP_MAPBOX_TOKEN ? (
            <div style={{ padding: '20px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px' }}>
              <p><strong>Warning:</strong> MapBox token not configured!</p>
              <p>Please add REACT_APP_MAPBOX_TOKEN to your .env file to display the map.</p>
              <p>Get a free token at: <a href="https://account.mapbox.com/access-tokens/" target="_blank" rel="noopener noreferrer">mapbox.com</a></p>
            </div>
          ) : (
            <div style={{ height: 'calc(100% - 80px)' }}>
              <Map
                initialViewState={{
                  longitude: -106.4528, // Tijuana/San Diego border
                  latitude: 31.7479,
                  zoom: 12,
                }}
                style={{ width: '100%', height: '100%' }}
                mapStyle="mapbox://styles/gavargas/ck1yptdx72uqd1cn0x144h6sx"
                mapboxAccessToken={process.env.REACT_APP_MAPBOX_TOKEN}
              >
                {/* Render car markers */}
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
                        width: '16px',
                        height: '16px',
                        borderRadius: '50%',
                        backgroundColor: getCarColor(car.status),
                        border: selectedCarId === car.id ? '3px solid #ff0000' : '2px solid #fff',
                        boxShadow: '0 0 6px rgba(0,0,0,0.4)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                      title={`Car ${car.id} - ${car.status}`}
                    />
                  </Marker>
                ))}

                <NavigationControl position="top-right" />
              </Map>
            </div>
          )}
        </Card>
      </div>

      <div style={{ width: '320px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <Card>
          <H2>Live Metrics</H2>
          <FormGroup>
            <Switch
              checked={showMetrics}
              onChange={(e) => setShowMetrics((e.target as HTMLInputElement).checked)}
              label="Show Metrics"
            />
          </FormGroup>

          {showMetrics && simulationData && (
            <div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Total Cars on Map:</strong> {simulationData.cars.length}
              </div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Total Queue Length:</strong>{' '}
                {simulationData.queues.reduce((sum, q) => sum + q.length, 0)}
              </div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Active Stations:</strong>{' '}
                {simulationData.queues.reduce((sum, q) => sum + q.throughput, 0)}
              </div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Total Arrivals:</strong> {simulationData.metrics.total_arrivals}
              </div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Total Completions:</strong> {simulationData.metrics.total_completions}
              </div>
              {simulationData.metrics.average_wait_time !== null && simulationData.metrics.average_wait_time !== undefined && (
                <div style={{ marginBottom: '10px' }}>
                  <strong>Avg Wait Time:</strong>{' '}
                  {simulationData.metrics.average_wait_time.toFixed(1)} sec
                  ({(simulationData.metrics.average_wait_time / 60).toFixed(2)} min)
                </div>
              )}
            </div>
          )}

          {!simulationData && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
              <p>Waiting for simulation data...</p>
              <p style={{ fontSize: '12px' }}>Make sure the simulation is running</p>
            </div>
          )}
        </Card>

        <Card style={{ flex: 1, overflow: 'hidden' }}>
          <H2>Active Cars</H2>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {simulationData?.cars.length === 0 && (
              <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                <p>No cars currently in the system</p>
                {simulationData.metrics.total_completions > 0 && (
                  <p style={{ fontSize: '12px' }}>
                    {simulationData.metrics.total_completions} cars have completed
                  </p>
                )}
              </div>
            )}
            {simulationData?.cars.map((car) => (
              <div
                key={car.id}
                style={{
                  padding: '10px',
                  margin: '5px 0',
                  backgroundColor: selectedCarId === car.id ? '#e1f5fe' : '#f8f9fa',
                  border: selectedCarId === car.id ? '2px solid #2196f3' : '1px solid #dee2e6',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onClick={() => setSelectedCarId(car.id)}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                  🚗 Car {car.id}
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  <div>
                    Status: <span style={{ color: getCarColor(car.status), fontWeight: 'bold' }}>
                      {car.status}
                    </span>
                  </div>
                  {car.velocity !== undefined && (
                    <div>Speed: {car.velocity.toFixed(1)} m/s</div>
                  )}
                  {car.queue_id !== undefined && car.queue_id !== null && (
                    <div>Queue: {car.queue_id}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {selectedCarId && (
          <Card>
            <H2>Car Details</H2>
            {(() => {
              const car = simulationData?.cars.find((c) => c.id === selectedCarId);
              if (!car) {
                return <div>Car not found</div>;
              }
              return (
                <div>
                  <Button
                    small
                    minimal
                    onClick={() => setSelectedCarId(null)}
                    style={{ marginBottom: '10px' }}
                  >
                    × Close
                  </Button>
                  <div style={{ fontSize: '14px' }}>
                    <div><strong>ID:</strong> {car.id}</div>
                    <div><strong>Status:</strong> {car.status}</div>
                    <div><strong>Position:</strong> [{car.position[1].toFixed(6)}, {car.position[0].toFixed(6)}]</div>
                    {car.velocity !== undefined && (
                      <div><strong>Velocity:</strong> {car.velocity.toFixed(2)} m/s</div>
                    )}
                    {car.acceleration !== undefined && (
                      <div><strong>Acceleration:</strong> {car.acceleration.toFixed(2)} m/s²</div>
                    )}
                    {car.queue_id !== undefined && car.queue_id !== null && (
                      <div><strong>Queue ID:</strong> {car.queue_id}</div>
                    )}
                  </div>
                </div>
              );
            })()}
          </Card>
        )}
      </div>
    </div>
  );
};

export default SimpleMapView;
