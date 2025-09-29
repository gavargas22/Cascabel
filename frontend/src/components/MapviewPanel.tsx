import React, { useRef, useEffect, useState } from 'react';
import { Card, H2, Button, ControlGroup, NumericInput, Switch, FormGroup } from '@blueprintjs/core';
import { api } from '../services/api';

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
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartCanvasRef = useRef<HTMLCanvasElement>(null);
  const barChartCanvasRef = useRef<HTMLCanvasElement>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [simulationData, setSimulationData] = useState<SimulationUpdate['data'] | null>(null);
  const [chartData, setChartData] = useState<{ time: number; queueLength: number }[]>([]);
  const [zoom, setZoom] = useState(1);
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
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw border crossing (simplified)
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(50 * zoom, 300 * zoom);
        ctx.lineTo(750 * zoom, 300 * zoom);
        ctx.stroke();

        if (telemetryMode && telemetryData.length > 0) {
          // Telemetry playback mode
          const currentTime = new Date(telemetryData[0]?.timestamp).getTime() + (playbackTime * 1000);

          // Group telemetry by car
          const carPaths: { [carId: string]: any[] } = {};
          telemetryData.forEach((record: any) => {
            const carId = record.car_id || record.id;
            if (!carPaths[carId]) carPaths[carId] = [];
            carPaths[carId].push(record);
          });

          // Draw car paths and current positions
          Object.entries(carPaths).forEach(([carId, records]) => {
            // Draw path
            ctx.strokeStyle = '#666';
            ctx.lineWidth = 2;
            ctx.beginPath();
            records.forEach((record, index) => {
              const x = ((record.longitude + 106.4850) * 1000 + 400) * zoom;
              const y = ((31.7619 - record.latitude) * 1000 + 300) * zoom;
              if (index === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            });
            ctx.stroke();

            // Find current position at playback time
            const currentRecord = records.find((record, index) => {
              const recordTime = new Date(record.timestamp).getTime();
              const nextRecordTime = records[index + 1] ? new Date(records[index + 1].timestamp).getTime() : recordTime;
              return recordTime <= currentTime && currentTime <= nextRecordTime;
            });

            if (currentRecord) {
              const x = ((currentRecord.longitude + 106.4850) * 1000 + 400) * zoom;
              const y = ((31.7619 - currentRecord.latitude) * 1000 + 300) * zoom;
              const isSelected = (currentRecord.car_id || currentRecord.id) === selectedCarId;
              ctx.fillStyle = currentRecord.status === 'arriving' ? 'blue' :
                currentRecord.status === 'queued' ? 'yellow' :
                  currentRecord.status === 'serving' ? 'orange' : 'green';
              ctx.beginPath();
              ctx.arc(x, y, isSelected ? 8 * zoom : 6 * zoom, 0, 2 * Math.PI);
              ctx.fill();
              if (isSelected) {
                ctx.strokeStyle = '#ff0000';
                ctx.lineWidth = 2;
                ctx.stroke();
              }
            }
          });
        } else if (simulationData) {
          // Live simulation mode
          // Draw cars
          simulationData.cars.forEach(car => {
            const x = (car.position[0] * 10 + 50) * zoom;
            const y = (car.position[1] * 10 + 300) * zoom;
            const isSelected = car.id === selectedCarId;
            ctx.fillStyle = car.status === 'approaching' ? 'blue' :
              car.status === 'queued' ? 'yellow' :
                car.status === 'serving' ? 'orange' : 'green';
            ctx.beginPath();
            ctx.arc(x, y, isSelected ? 7 * zoom : 5 * zoom, 0, 2 * Math.PI);
            ctx.fill();
            if (isSelected) {
              ctx.strokeStyle = '#ff0000';
              ctx.lineWidth = 2;
              ctx.stroke();
            }
          });

          // Show queue lengths
          if (showQueueLengths) {
            simulationData.queues.forEach((queue, index) => {
              ctx.fillStyle = '#000';
              ctx.fillText(`Q${index}: ${queue.length}`, 50 + index * 100, 50);
            });
          }
        } else {
          // Placeholder
          ctx.fillStyle = '#f0f0f0';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = '#000';
          ctx.font = '20px Arial';
          ctx.fillText('Map Canvas Placeholder', 50, 50);
        }
      }
    }
  }, [simulationData, zoom, showTrails, showQueueLengths, telemetryMode, telemetryData, playbackTime]);

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
    console.log('Settings applied:', { zoom, refreshRate, showTrails, showQueueLengths });
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
        <Card>
          <H2>Simulation Mapview - ID: {simulationId}</H2>
          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            style={{ border: '1px solid #ccc', backgroundColor: '#fff' }}
            aria-label="Map canvas"
          />
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
            <FormGroup label="Zoom Level">
              <NumericInput
                value={zoom}
                onValueChange={setZoom}
                min={0.5}
                max={5}
                stepSize={0.1}
                minorStepSize={0.1}
                majorStepSize={1}
                fill
              />
            </FormGroup>
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