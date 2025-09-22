import React, { useState } from 'react';
import {
  Button,
  Card,
  FormGroup,
  NumericInput,
  HTMLSelect,
  H2,
  H3,
  H4,
  Divider,
  Callout,
  Tag
} from '@blueprintjs/core';
import { ServiceNode, PhoneConfig } from '../services/api';
import './ControlPanel.css';

interface ControlPanelProps {
  simulationId: string | null;
  serviceNodes: ServiceNode[];
  onAddCar: (phoneConfig?: PhoneConfig) => Promise<void>;
  onUpdateServiceNode: (nodeId: string, rate: number) => Promise<void>;
  onStartSimulation: () => Promise<void>;
  onStopSimulation: () => Promise<void>;
  isRunning: boolean;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  simulationId,
  serviceNodes,
  onAddCar,
  onUpdateServiceNode,
  onStartSimulation,
  onStopSimulation,
  isRunning,
}) => {
  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig>({
    sampling_rate: 10,
    gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 3.0 },
    accelerometer_noise: 0.01,
    gyro_noise: 0.001,
    device_orientation: 'portrait',
  });

  const [nodeRates, setNodeRates] = useState<{ [nodeId: string]: number }>({});
  const [isAddingCar, setIsAddingCar] = useState(false);

  const handleAddCar = async () => {
    setIsAddingCar(true);
    try {
      await onAddCar(phoneConfig);
    } catch (error) {
      console.error('Failed to add car:', error);
      alert('Failed to add car. Please try again.');
    } finally {
      setIsAddingCar(false);
    }
  };

  const handleUpdateNodeRate = async (nodeId: string, rate: number) => {
    try {
      await onUpdateServiceNode(nodeId, rate);
      setNodeRates(prev => ({ ...prev, [nodeId]: rate }));
    } catch (error) {
      console.error('Failed to update service node rate:', error);
      alert('Failed to update service node rate. Please try again.');
    }
  };

  const groupedNodes = serviceNodes.reduce((acc, node) => {
    if (!acc[node.queue_id]) {
      acc[node.queue_id] = [];
    }
    acc[node.queue_id].push(node);
    return acc;
  }, {} as { [queueId: number]: ServiceNode[] });

  return (
    <Card className="control-panel">
      <H2>Control Panel</H2>

      {/* Simulation Controls */}
      <div className="simulation-controls">
        <H3>Simulation Control</H3>
        <div className="control-buttons">
          {!simulationId ? (
            <Button
              intent="primary"
              icon="play"
              onClick={onStartSimulation}
              large
            >
              Start New Simulation
            </Button>
          ) : (
            <>
              <Button
                intent="success"
                icon="add"
                onClick={handleAddCar}
                disabled={isAddingCar || !isRunning}
                loading={isAddingCar}
              >
                Add Car
              </Button>
              <Button
                intent="danger"
                icon="stop"
                onClick={onStopSimulation}
              >
                Stop Simulation
              </Button>
            </>
          )}
        </div>
        {simulationId && (
          <Callout className="simulation-info">
            <strong>Simulation ID:</strong> {simulationId}<br />
            <strong>Status:</strong> <Tag intent={isRunning ? "success" : "warning"}>
              {isRunning ? 'Running' : 'Stopped'}
            </Tag>
          </Callout>
        )}
      </div>

      {/* Phone Configuration */}
      {simulationId && (
        <div className="phone-config">
          <Divider />
          <H3>Phone Configuration</H3>
          <div className="config-grid">
            <FormGroup label="Sampling Rate (Hz)">
              <NumericInput
                value={phoneConfig.sampling_rate}
                onValueChange={(value) => setPhoneConfig(prev => ({
                  ...prev,
                  sampling_rate: value || 10
                }))}
                min={1}
                max={100}
                fill
              />
            </FormGroup>

            <FormGroup label="GPS Horizontal Accuracy">
              <NumericInput
                value={phoneConfig.gps_noise.horizontal_accuracy}
                onValueChange={(value) => setPhoneConfig(prev => ({
                  ...prev,
                  gps_noise: {
                    ...prev.gps_noise,
                    horizontal_accuracy: value || 5.0
                  }
                }))}
                min={0}
                stepSize={0.1}
                fill
              />
            </FormGroup>

            <FormGroup label="GPS Vertical Accuracy">
              <NumericInput
                value={phoneConfig.gps_noise.vertical_accuracy}
                onValueChange={(value) => setPhoneConfig(prev => ({
                  ...prev,
                  gps_noise: {
                    ...prev.gps_noise,
                    vertical_accuracy: value || 3.0
                  }
                }))}
                min={0}
                stepSize={0.1}
                fill
              />
            </FormGroup>

            <FormGroup label="Accelerometer Noise">
              <NumericInput
                value={phoneConfig.accelerometer_noise}
                onValueChange={(value) => setPhoneConfig(prev => ({
                  ...prev,
                  accelerometer_noise: value || 0.01
                }))}
                min={0}
                stepSize={0.001}
                fill
              />
            </FormGroup>

            <FormGroup label="Gyroscope Noise">
              <NumericInput
                value={phoneConfig.gyro_noise}
                onValueChange={(value) => setPhoneConfig(prev => ({
                  ...prev,
                  gyro_noise: value || 0.001
                }))}
                min={0}
                stepSize={0.0001}
                fill
              />
            </FormGroup>

            <FormGroup label="Device Orientation">
              <HTMLSelect
                value={phoneConfig.device_orientation}
                onChange={(e) => setPhoneConfig(prev => ({
                  ...prev,
                  device_orientation: e.target.value as 'portrait' | 'landscape'
                }))}
                fill
              >
                <option value="portrait">Portrait</option>
                <option value="landscape">Landscape</option>
              </HTMLSelect>
            </FormGroup>
          </div>
        </div>
      )}

      {/* Service Node Controls */}
      {simulationId && Object.keys(groupedNodes).length > 0 && (
        <div className="service-node-controls">
          <Divider />
          <H3>Service Node Tuning</H3>
          {Object.entries(groupedNodes).map(([queueId, nodes]) => (
            <Card key={queueId} className="queue-nodes">
              <H4>Queue {parseInt(queueId) + 1}</H4>
              <div className="nodes-grid">
                {nodes.map(node => (
                  <Card key={node.node_id} className="node-control">
                    <div className="node-info">
                      <span className="node-id">{node.node_id}</span>
                      <Tag intent={node.is_busy ? "danger" : "success"} minimal>
                        {node.is_busy ? 'Busy' : 'Free'}
                      </Tag>
                    </div>
                    <FormGroup label="Rate (cars/min)">
                      <div className="rate-control">
                        <NumericInput
                          value={nodeRates[node.node_id] ?? node.service_rate}
                          onValueChange={(value) => {
                            const newRate = value || node.service_rate;
                            setNodeRates(prev => ({ ...prev, [node.node_id]: newRate }));
                          }}
                          min={0.1}
                          max={10}
                          stepSize={0.1}
                          fill
                        />
                        <Button
                          intent="primary"
                          onClick={() => handleUpdateNodeRate(
                            node.node_id,
                            nodeRates[node.node_id] ?? node.service_rate
                          )}
                          small
                        >
                          Update
                        </Button>
                      </div>
                    </FormGroup>
                    <div className="node-stats">
                      <Callout>
                        <strong>Served:</strong> {node.total_served}<br />
                        <strong>Avg Time:</strong> {node.total_served > 0 ?
                          (node.total_service_time / node.total_served).toFixed(1) : '0.0'}s
                      </Callout>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </Card>
  );
};

export default ControlPanel;