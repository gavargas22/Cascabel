import React from 'react';
import { Card, H2, H3, Tag, Tooltip } from '@blueprintjs/core';
import { Car, ServiceNode } from '../services/api';
import './QueueVisualization.css';

interface QueueVisualizationProps {
  cars: Car[];
  serviceNodes: ServiceNode[];
  numQueues: number;
  selectedCarId?: number;
  onCarSelect: (carId: number) => void;
}

const QueueVisualization: React.FC<QueueVisualizationProps> = ({
  cars,
  serviceNodes,
  numQueues,
  selectedCarId,
  onCarSelect,
}) => {
  // Group cars by queue
  const carsByQueue: { [queueId: number]: Car[] } = {};
  for (let i = 0; i < numQueues; i++) {
    carsByQueue[i] = [];
  }

  cars.forEach(car => {
    if (car.queue_id !== undefined) {
      carsByQueue[car.queue_id].push(car);
    }
  });

  // Group service nodes by queue
  const nodesByQueue: { [queueId: number]: ServiceNode[] } = {};
  for (let i = 0; i < numQueues; i++) {
    nodesByQueue[i] = [];
  }

  serviceNodes.forEach(node => {
    nodesByQueue[node.queue_id].push(node);
  });

  const getCarColor = (car: Car) => {
    switch (car.status) {
      case 'arriving': return '#4CAF50'; // Green
      case 'queued': return '#FF9800';   // Orange
      case 'serving': return '#2196F3';  // Blue
      case 'completed': return '#9C27B0'; // Purple
      default: return '#757575';         // Grey
    }
  };

  const getNodeColor = (node: ServiceNode) => {
    return node.is_busy ? '#F44336' : '#4CAF50'; // Red if busy, green if free
  };

  return (
    <Card className="queue-visualization">
      <H2>Queue Visualization</H2>
      <div className="queues-container">
        {Array.from({ length: numQueues }, (_, queueId) => (
          <Card key={queueId} className="queue">
            <H3>Queue {queueId + 1}</H3>

            {/* Service Nodes */}
            <div className="service-nodes">
              {nodesByQueue[queueId].map(node => (
                <Tooltip
                  key={node.node_id}
                  content={`Node ${node.node_id}: ${node.is_busy ? 'Busy' : 'Free'} (${node.service_rate.toFixed(1)} cars/min)`}
                >
                  <div
                    className="service-node"
                    style={{ backgroundColor: getNodeColor(node) }}
                  >
                    <div className="node-label">{node.node_id.split('_')[1]}</div>
                    {node.is_busy && node.current_car_id && (
                      <div className="serving-car">Car {node.current_car_id}</div>
                    )}
                  </div>
                </Tooltip>
              ))}
            </div>

            {/* Cars in Queue */}
            <div className="queue-cars">
              {carsByQueue[queueId]
                .sort((a, b) => a.position - b.position) // Sort by position
                .map(car => (
                  <Tooltip
                    key={car.car_id}
                    content={`Car ${car.car_id}: ${car.status} (${car.velocity.toFixed(1)} m/s)`}
                  >
                    <div
                      className={`car ${selectedCarId === car.car_id ? 'selected' : ''}`}
                      style={{ backgroundColor: getCarColor(car) }}
                      onClick={() => onCarSelect(car.car_id)}
                    >
                      <div className="car-id">{car.car_id}</div>
                      <Tag
                        intent={
                          car.status === 'arriving' ? 'success' :
                          car.status === 'queued' ? 'warning' :
                          car.status === 'serving' ? 'primary' :
                          car.status === 'completed' ? 'none' : 'none'
                        }
                        minimal
                      >
                        {car.status[0].toUpperCase()}
                      </Tag>
                    </div>
                  </Tooltip>
                ))}
            </div>
          </Card>
        ))}
      </div>
    </Card>
  );
};

export default QueueVisualization;