import React, { useRef, useEffect, useState } from 'react';
import { Card, H2, Button, ControlGroup, NumericInput, Switch, FormGroup } from '@blueprintjs/core';
import Map, { Marker, Source, Layer, NavigationControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { api } from '../services/api';

// Import API_BASE_URL for GeoJSON endpoint
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface MapviewPanelProps {
  simulationId: string;
}

interface SimulationUpdate {
  type: 'simulation_update';
  data: {
    cars: Array<{
      id: string;
      position: [number, number];
      status: 'approaching' | 'queued' | 'serving' | 'completed';
    }>,
    queues: Array<{
      length: number;
      throughput: number;
    }>,
    metrics: {
      total_arrivals: number;
      total_completions: number;
      average_wait_time: number;
    };
  };
}

const MapviewPanel: React.FC<MapviewPanelProps> = ({ simulationId }) => {
  const mapRef = useRef<any>(null);
  const chartCanvasRef = useRef<HTMLCanvasElement>(null);
  const barChartCanvasRef = useRef<HTMLCanvasElement>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [simulationData, setSimulationData] = useState<SimulationUpdate['data'] | null>(null);
  const [chartData, setChartData] = useState<{ time: number; queueLength: number }[]>([]);
  const [refreshRate, setRefreshRate] = useState(1000);
  const [showTrails, setShowTrails] = useState(false);
  const [showQueueLengths, setShowQueueLengths] = useState(false);
  const [carTrails, setCarTrails] = useState<{ [id: string]: [number, number][] }>({});
  const [telemetryMode, setTelemetryMode] = useState(false);
  const [telemetryData, setTelemetryData] = useState<any[]>([]);
  const [playbackTime, setPlaybackTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedCarId, setSelectedCarId] = useState<string | null>(null);

  const loadTelemetryData = async () => {
    try {
      const response = await fetch(`/api/simulation/${simulationId}/telemetry`);
      if (response.ok) {
        const data = await response.json();
        setTelemetryData(data.telemetry || []);
      }
    } catch (error) {
      console.error('Failed to load telemetry data:', error);
    }
  };

  useEffect(() => {
    const websocket = new WebSocket(`${api.WS_BASE_URL}/ws/${simulationId}`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
      try {
        const message: SimulationUpdate = JSON.parse(event.data);
        if (message.type === 'simulation_update') {
          setSimulationData(message.data);
          // Add to chart data
          setChartData(prev => [...prev.slice(-50), { // Keep last 50 points
            time: Date.now(),
            queueLength: message.data.queues.reduce((sum, q) => sum + q.length, 0)
          }]);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected, attempting to reconnect...');
      setTimeout(() => {
        const newWs = new WebSocket(`${api.WS_BASE_URL}/ws/${simulationId}`);
        // Reattach event listeners
        newWs.onopen = websocket.onopen;
        newWs.onmessage = websocket.onmessage;
        newWs.onclose = websocket.onclose;
        newWs.onerror = websocket.onerror;
        setWs(newWs);
      }, 1000);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [simulationId]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (map && telemetryData.length > 0) {
      // Calculate bounds from telemetry data
      const bounds = telemetryData.reduce(
        (acc: any, point: any) => ({
          minLng: Math.min(acc.minLng, point.longitude),
          maxLng: Math.max(acc.maxLng, point.longitude),
          minLat: Math.min(acc.minLat, point.latitude),
          maxLat: Math.max(acc.maxLat, point.latitude),
        }),
        {
          minLng: Infinity,
          maxLng: -Infinity,
          minLat: Infinity,
          maxLat: -Infinity,
        }
      );

      // Fit map to bounds with padding
      map.fitBounds(
        [[bounds.minLng, bounds.minLat], [bounds.maxLng, bounds.maxLat]],
        { padding: 50, duration: 1000 }
      );
    }
  }, [telemetryData]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (map && simulationData) {
      // Update car markers
      const carFeatures = simulationData.cars.map(car => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [car.position[0], car.position[1]],
        },
        properties: {
          id: car.id,
          status: car.status,
        },
      }));

      // Update queue markers
      const queueFeatures = simulationData.queues.map((queue, index) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [index * 0.01, 0], // Dummy coordinates
        },
        properties: {
          length: queue.length,
          throughput: queue.throughput,
        },
      }));

      // Add sources and layers for cars and queues
      mapRef.current.setProps({
        children: (
          <>
            <Source id="cars" type="geojson" data={{ type: 'FeatureCollection', features: carFeatures }} />
            <Layer
              id="car-points"
              type="circle"
              source="cars"
              paint={{
                'circle-radius': 6,
                'circle-color': [
                  'match',
                  ['get', 'status'],
                  'approaching', '#007bff',
                  'queued', '#ffc107',
                  'serving', '#28a745',
                  'completed', '#dc3545',
                  '#ccc'
                ],
                'circle-stroke-color': '#fff',
                'circle-stroke-width': 2,
              }}
            />
            <Source id="queues" type="geojson" data={{ type: 'FeatureCollection', features: queueFeatures }} />
            <Layer
              id="queue-points"
              type="circle"
              source="queues"
              paint={{
                'circle-radius': 4,
                'circle-color': '#007bff',
                'circle-opacity': 0.6,
              }}
            />
          </>
        ),
      });
    }
  }, [simulationData]);

  useEffect(() => {
    const canvas = chartCanvasRef.current;
    if (canvas && chartData.length > 1) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        const maxLength = Math.max(...chartData.map(d => d.queueLength));
        chartData.forEach((point, index) => {
          const x = (index / (chartData.length - 1)) * canvas.width;
          const y = canvas.height - (point.queueLength / maxLength) * canvas.height;
          if (index === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
      }
    }
  }, [chartData]);

  useEffect(() => {
    const canvas = barChartCanvasRef.current;
    if (canvas && simulationData) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const barWidth = canvas.width / 2 - 20;
        const maxHeight = canvas.height - 20;

        // Throughput bar
        const throughput = simulationData.queues.reduce((sum, q) => sum + q.throughput, 0);
        const throughputHeight = (throughput / 10) * maxHeight; // Assume max 10
        ctx.fillStyle = '#28a745';
        ctx.fillRect(10, canvas.height - throughputHeight - 10, barWidth, throughputHeight);
        ctx.fillStyle = '#000';
        ctx.fillText(`Throughput: ${throughput}`, 10, canvas.height - 5);

        // Wait time bar
        const waitTime = simulationData.metrics.average_wait_time;
        const waitHeight = (waitTime / 100) * maxHeight; // Assume max 100
        ctx.fillStyle = '#dc3545';
        ctx.fillRect(10 + barWidth + 20, canvas.height - waitHeight - 10, barWidth, waitHeight);
        ctx.fillStyle = '#000';
        ctx.fillText(`Wait Time: ${waitTime?.toFixed(1)}`, 10 + barWidth + 20, canvas.height - 5);
      }
    }
  }, [simulationData]);

  const handleApplySettings = () => {
    // Implement any settings application logic here
    console.log('Settings applied:', { refreshRate, showTrails, showQueueLengths });
  };

  useEffect(() => {
    if (telemetryMode) {
      loadTelemetryData();
    }
  }, [telemetryMode, simulationId]);

  // Playback animation
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (telemetryMode && isPlaying && telemetryData.length > 0) {
      interval = setInterval(() => {
        setPlaybackTime(prev => {
          const maxTime = (new Date(telemetryData[telemetryData.length - 1]?.timestamp).getTime() -
            new Date(telemetryData[0]?.timestamp).getTime()) / 1000;
          const nextTime = prev + (1 / 30) * playbackSpeed; // 30 FPS
          return nextTime >= maxTime ? 0 : nextTime; // Loop back to start
        });
      }, 1000 / 30); // 30 FPS
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [telemetryMode, isPlaying, telemetryData, playbackSpeed]);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <div style={{ flex: 1, padding: '10px' }}>
        <Card style={{ height: '600px', overflow: 'hidden' }}>
          <H2>Simulation Mapview - ID: {simulationId}</H2>
          <Map
            ref={mapRef}
            initialViewState={{
              longitude: -106.4528, // Tijuana/San Diego border crossing
              latitude: 31.7479,
              zoom: 10,
              pitch: 0,
              bearing: 0,
            }}
            style={{ width: '100%', height: '100%' }}
            mapStyle="mapbox://styles/gavargas/ck1yptdx72uqd1cn0x144h6sx"
            mapboxAccessToken={process.env.REACT_APP_MAPBOX_TOKEN}
          >
            {/* Car markers - limit rendering for performance */}
            {simulationData?.cars.slice(0, 100).map(car => (
              <Marker
                key={car.id}
                longitude={car.position[0]}
                latitude={car.position[1]}
                anchor="center"
                onClick={() => setSelectedCarId(car.id)}
              >
                <div
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor:
                      car.status === 'approaching' ? '#007bff' :
                        car.status === 'queued' ? '#ffc107' :
                          car.status === 'serving' ? '#28a745' :
                            car.status === 'completed' ? '#dc3545' : '#ccc',
                    border: selectedCarId === car.id ? '3px solid #ff0000' : '2px solid #fff',
                    boxShadow: '0 0 4px rgba(0,0,0,0.3)',
                    cursor: 'pointer',
                  }}
                  title={`Car ${car.id} - ${car.status}`}
                />
              </Marker>
            ))}

            {/* Border geometry overlay */}
            <Source
              id="border-path"
              type="geojson"
              data={`${API_BASE_URL}/geojson/usa2mx/bota`}
            />
            <Layer
              id="border-path-line"
              type="line"
              source="border-path"
              paint={{
                'line-color': '#ff0000',
                'line-width': 3,
                'line-opacity': 0.8,
              }}
            />

            {/* Animated telemetry markers */}
            {telemetryMode && isPlaying && telemetryData.length > 0 && (
              <>
                {(Object.entries(
                  telemetryData.reduce((acc: any, point: any) => {
                    if (!acc[point.car_id]) acc[point.car_id] = [];
                    acc[point.car_id].push(point);
                    return acc;
                  }, {} as Record<string, any[]>)
                ) as [string, any][]).map(([carId, points]) => {
                  // Find the current position based on playback time
                  const currentPoint = points.find((point: any, index: number) => {
                    const nextPoint = points[index + 1];
                    if (!nextPoint) return true;
                    return point.timestamp <= playbackTime && nextPoint.timestamp > playbackTime;
                  }) || points[points.length - 1];

                  return (
                    <Marker
                      key={`animated-${carId}`}
                      longitude={currentPoint.longitude}
                      latitude={currentPoint.latitude}
                      anchor="center"
                    >
                      <div
                        style={{
                          width: '16px',
                          height: '16px',
                          borderRadius: '50%',
                          backgroundColor: selectedCarId === carId ? '#ff0000' : '#007bff',
                          border: '3px solid #fff',
                          boxShadow: '0 0 8px rgba(0,0,0,0.5)',
                          animation: 'pulse 1s infinite',
                        }}
                        title={`Car ${carId} - ${currentPoint.status}`}
                      />
                    </Marker>
                  );
                })}
              </>
            )}

            {/* Telemetry paths */}
            {telemetryMode && telemetryData.length > 0 && (
              <>
                <Source
                  id="telemetry-paths"
                  type="geojson"
                  data={{
                    type: 'FeatureCollection',
                    features: Object.entries(
                      telemetryData.reduce((acc: any, point: any) => {
                        if (!acc[point.car_id]) acc[point.car_id] = [];
                        acc[point.car_id].push([point.longitude, point.latitude]);
                        return acc;
                      }, {})
                    ).map(([carId, coordinates]: [string, any]) => ({
                      type: 'Feature',
                      geometry: {
                        type: 'LineString',
                        coordinates: coordinates,
                      },
                      properties: {
                        carId: carId,
                        selected: selectedCarId === carId,
                      },
                    })),
                  }}
                />
                <Layer
                  id="telemetry-paths-line"
                  type="line"
                  source="telemetry-paths"
                  paint={{
                    'line-color': ['case',
                      ['==', ['get', 'selected'], true], '#ff0000',
                      '#007bff'
                    ],
                    'line-width': ['case',
                      ['==', ['get', 'selected'], true], 4,
                      2
                    ],
                    'line-opacity': 0.7,
                  }}
                />
              </>
            )}

            <NavigationControl position="top-right" />
          </Map>
        </Card>
        <Card style={{ marginTop: '10px' }}>
          <H2>Queue Length Over Time</H2>
          <canvas
            ref={chartCanvasRef}
            width={800}
            height={200}
            style={{ border: '1px solid #ccc', backgroundColor: '#fff' }}
            aria-label="Queue length chart"
          />
        </Card>
        <Card style={{ marginTop: '10px' }}>
          <H2>Current Metrics</H2>
          <canvas
            ref={barChartCanvasRef}
            width={400}
            height={150}
            style={{ border: '1px solid #ccc', backgroundColor: '#fff' }}
            aria-label="Metrics bar chart"
          />
        </Card>
      </div>
      <div style={{ width: '300px', padding: '10px' }}>
        <Card>
          <H2>Visualization Controls</H2>
          <ControlGroup vertical>
            <FormGroup label="Refresh Rate (ms)">
              <NumericInput
                value={refreshRate}
                onValueChange={setRefreshRate}
                min={100}
                max={5000}
                stepSize={100}
                minorStepSize={100}
                majorStepSize={1000}
                fill
              />
            </FormGroup>
            <Switch
              label="Show Car Trails"
              checked={showTrails}
              onChange={(e) => setShowTrails((e.target as HTMLInputElement).checked)}
            />
            <Switch
              label="Show Queue Lengths"
              checked={showQueueLengths}
              onChange={(e) => setShowQueueLengths((e.target as HTMLInputElement).checked)}
            />
            <Switch
              label="Telemetry Mode"
              checked={telemetryMode}
              onChange={(e) => setTelemetryMode((e.target as HTMLInputElement).checked)}
            />
            {telemetryMode && (
              <>
                <FormGroup label="Playback Speed">
                  <NumericInput
                    value={playbackSpeed}
                    onValueChange={setPlaybackSpeed}
                    min={0.1}
                    max={4}
                    stepSize={0.1}
                    fill
                  />
                </FormGroup>
                <Button
                  intent={isPlaying ? "danger" : "success"}
                  fill
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? "Pause" : "Play"}
                </Button>
                <FormGroup label="Playback Time">
                  <NumericInput
                    value={playbackTime}
                    onValueChange={setPlaybackTime}
                    min={0}
                    max={telemetryData.length > 0 ?
                      (new Date(telemetryData[telemetryData.length - 1]?.timestamp).getTime() -
                        new Date(telemetryData[0]?.timestamp).getTime()) / 1000 : 0}
                    stepSize={1}
                    fill
                  />
                </FormGroup>
              </>
            )}
            <Button intent="primary" fill onClick={handleApplySettings}>
              Apply Settings
            </Button>
          </ControlGroup>
        </Card>
        <Card style={{ marginTop: '10px' }}>
          <H2>Live Metrics</H2>
          <p>Queue Length: {simulationData?.queues.reduce((sum, q) => sum + q.length, 0) || '--'}</p>
          <p>Throughput: {simulationData?.queues.reduce((sum, q) => sum + q.throughput, 0) || '--'} cars/min</p>
          <p>Avg Wait Time: {simulationData?.metrics.average_wait_time?.toFixed(1) || '--'} sec</p>
        </Card>
        <Card style={{ marginTop: '10px' }}>
          <H2>Car List</H2>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {(telemetryMode ? telemetryData : simulationData?.cars || []).map((car: any) => {
              const carId = telemetryMode ? car.car_id || car.id : car.id;
              const isSelected = selectedCarId === carId;
              return (
                <div
                  key={carId}
                  style={{
                    padding: '8px',
                    margin: '4px 0',
                    backgroundColor: isSelected ? '#e1f5fe' : '#f5f5f5',
                    border: isSelected ? '2px solid #2196f3' : '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                  onClick={() => setSelectedCarId(carId)}
                >
                  <div style={{ fontWeight: 'bold' }}>Car {carId}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    Status: {car.status}
                  </div>
                  {telemetryMode && (
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      Speed: {car.velocity?.toFixed(1)} m/s
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
        {selectedCarId && (
          <Card style={{ marginTop: '10px' }}>
            <H2>Car Dashboard - {selectedCarId}</H2>
            {(() => {
              const car = (telemetryMode ? telemetryData : simulationData?.cars || [])
                .find((c: any) => (telemetryMode ? c.car_id || c.id : c.id) === selectedCarId);
              if (!car) return <div>No data available</div>;

              return (
                <div>
                  <p><strong>Status:</strong> {car.status}</p>
                  {telemetryMode ? (
                    <>
                      <p><strong>Position:</strong> {car.latitude?.toFixed(6)}, {car.longitude?.toFixed(6)}</p>
                      <p><strong>Velocity:</strong> {car.velocity?.toFixed(2)} m/s</p>
                      <p><strong>Acceleration:</strong> {car.acceleration?.toFixed(2)} m/s²</p>
                      <p><strong>Queue ID:</strong> {car.queue_id || 'None'}</p>
                      <p><strong>Distance Traveled:</strong> {car.distance_traveled?.toFixed(2)} m</p>
                    </>
                  ) : (
                    <>
                      <p><strong>Position:</strong> {car.position?.join(', ')}</p>
                      <p><strong>Velocity:</strong> {car.velocity?.toFixed(2)} m/s</p>
                      <p><strong>Acceleration:</strong> {car.acceleration?.toFixed(2)} m/s²</p>
                      <p><strong>Queue ID:</strong> {car.queue_id}</p>
                    </>
                  )}
                </div>
              );
            })()}
          </Card>
        )}
      </div>
    </div>
  );
};

export default MapviewPanel;