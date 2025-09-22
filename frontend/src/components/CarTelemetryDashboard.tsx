import React from 'react';
import { Card, H2, H3, H4, Tag, Callout } from '@blueprintjs/core';
import { Car } from '../services/api';
import './CarTelemetryDashboard.css';

interface CarTelemetryDashboardProps {
  cars: Car[];
  selectedCarId?: number;
  onCarSelect: (carId: number) => void;
}

const CarTelemetryDashboard: React.FC<CarTelemetryDashboardProps> = ({
  cars,
  selectedCarId,
  onCarSelect,
}) => {
  const selectedCar = cars.find(car => car.car_id === selectedCarId);

  return (
    <Card className="telemetry-dashboard">
      <H2>Car Telemetry Dashboard</H2>

      <div className="dashboard-content">
        {/* Car List */}
        <Card className="car-list">
          <H3>All Cars ({cars.length})</H3>
          <div className="car-grid">
            {cars.map(car => (
              <Card
                key={car.car_id}
                className={`car-item ${selectedCarId === car.car_id ? 'selected' : ''}`}
                interactive
                onClick={() => onCarSelect(car.car_id)}
              >
                <div className="car-header">
                  <span className="car-id">Car {car.car_id}</span>
                  <Tag
                    intent={
                      car.status === 'arriving' ? 'success' :
                      car.status === 'queued' ? 'warning' :
                      car.status === 'serving' ? 'primary' :
                      car.status === 'completed' ? 'none' : 'none'
                    }
                  >
                    {car.status}
                  </Tag>
                </div>
                <div className="car-metrics">
                  <div>Position: {car.position.toFixed(1)}m</div>
                  <div>Velocity: {car.velocity.toFixed(1)} m/s</div>
                  {car.queue_id !== undefined && (
                    <div>Queue: {car.queue_id + 1}</div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </Card>

        {/* Selected Car Details */}
        <Card className="car-details">
          {selectedCar ? (
            <>
              <H3>Car {selectedCar.car_id} Details</H3>
              <div className="details-grid">
                <div className="detail-item">
                  <label>Status:</label>
                  <Tag
                    intent={
                      selectedCar.status === 'arriving' ? 'success' :
                      selectedCar.status === 'queued' ? 'warning' :
                      selectedCar.status === 'serving' ? 'primary' :
                      selectedCar.status === 'completed' ? 'none' : 'none'
                    }
                    large
                  >
                    {selectedCar.status.toUpperCase()}
                  </Tag>
                </div>

                <Callout>
                  <strong>Position:</strong> {selectedCar.position.toFixed(2)} meters
                </Callout>

                <Callout>
                  <strong>Velocity:</strong> {selectedCar.velocity.toFixed(2)} m/s
                </Callout>

                <Callout>
                  <strong>Acceleration:</strong> 0.00 m/s²
                </Callout>

                {selectedCar.queue_id !== undefined && (
                  <Callout>
                    <strong>Queue:</strong> Queue {selectedCar.queue_id + 1}
                  </Callout>
                )}

                <Callout>
                  <strong>GPS Coordinates:</strong> Lat: 0.0000, Lon: 0.0000
                </Callout>

                <Callout>
                  <strong>Device Orientation:</strong> Portrait
                </Callout>
              </div>

              {/* Telemetry Charts Placeholder */}
              <div className="telemetry-charts">
                <H4>Real-time Telemetry</H4>
                <Card className="chart-placeholder">
                  <p>Accelerometer data would be displayed here</p>
                  <div className="placeholder-chart">📊</div>
                </Card>
                <Card className="chart-placeholder">
                  <p>GPS tracking would be displayed here</p>
                  <div className="placeholder-chart">🗺️</div>
                </Card>
              </div>
            </>
          ) : (
            <Callout className="no-selection">
              Select a car to view detailed telemetry
            </Callout>
          )}
        </Card>
      </div>
    </Card>
  );
};

export default CarTelemetryDashboard;