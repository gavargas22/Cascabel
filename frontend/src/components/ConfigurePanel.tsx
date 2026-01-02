import React, { useState } from 'react';
import {
  FormGroup,
  NumericInput,
  HTMLSelect,
  Checkbox,
  Button,
  Card,
  H3,
  Divider
} from '@blueprintjs/core';
import {
  BorderCrossingConfig,
  SimulationConfig,
  PhoneConfig
} from '../services/api';

interface ConfigurePanelProps {
  onConfigChange?: (config: {
    borderConfig: BorderCrossingConfig;
    simulationConfig: SimulationConfig;
    phoneConfig?: PhoneConfig;
  }) => void;
}

const ConfigurePanel: React.FC<ConfigurePanelProps> = ({ onConfigChange }) => {
  const [borderConfig, setBorderConfig] = useState<BorderCrossingConfig>({
    num_queues: 3,
    nodes_per_queue: [2, 3, 2],
    arrival_rate: 6.0,
    service_rates: [3.5, 3.0, 4.0, 3.2, 3.8, 3.1, 3.9],
    queue_assignment: 'shortest',
    safe_distance: 8.0,
    max_queue_length: 50
  });

  const [simulationConfig, setSimulationConfig] = useState<SimulationConfig>({
    max_simulation_time: 3600.0,
    time_factor: 1.0,
    enable_telemetry: true,
    enable_position_tracking: true
  });

  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig | undefined>({
    sampling_rate: 10.0,
    gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 10.0 },
    accelerometer_noise: 0.1,
    gyro_noise: 0.01,
    device_orientation: 'portrait'
  });

  const handleBorderConfigChange = (field: keyof BorderCrossingConfig, value: any) => {
    const newConfig = { ...borderConfig, [field]: value };
    setBorderConfig(newConfig);
    onConfigChange?.({ borderConfig: newConfig, simulationConfig, phoneConfig });
  };

  const handleSimulationConfigChange = (field: keyof SimulationConfig, value: any) => {
    const newConfig = { ...simulationConfig, [field]: value };
    setSimulationConfig(newConfig);
    onConfigChange?.({ borderConfig, simulationConfig: newConfig, phoneConfig });
  };

  const handlePhoneConfigChange = (field: keyof PhoneConfig, value: any) => {
    if (phoneConfig) {
      const newConfig = { ...phoneConfig, [field]: value };
      setPhoneConfig(newConfig);
      onConfigChange?.({ borderConfig, simulationConfig, phoneConfig: newConfig });
    }
  };

  const handleNodesPerQueueChange = (index: number, value: number) => {
    const newNodes = [...borderConfig.nodes_per_queue];
    newNodes[index] = value;
    handleBorderConfigChange('nodes_per_queue', newNodes);
  };

  const handleServiceRatesChange = (index: number, value: number) => {
    const newRates = [...borderConfig.service_rates];
    newRates[index] = value;
    handleBorderConfigChange('service_rates', newRates);
  };

  return (
    <div>
      <Card>
        <H3>Border Crossing Configuration</H3>
        <FormGroup label="Number of Queues" labelFor="num-queues">
          <NumericInput
            id="num-queues"
            value={borderConfig.num_queues}
            onValueChange={(value) => handleBorderConfigChange('num_queues', value)}
            min={1}
            max={10}
          />
        </FormGroup>

        <FormGroup label="Nodes per Queue" labelFor="nodes-per-queue">
          {borderConfig.nodes_per_queue.map((nodes, index) => (
            <NumericInput
              key={index}
              value={nodes}
              onValueChange={(value) => handleNodesPerQueueChange(index, value)}
              placeholder={`Queue ${index + 1}`}
              min={1}
              style={{ marginRight: '10px', width: '80px' }}
            />
          ))}
        </FormGroup>

        <FormGroup label="Arrival Rate" labelFor="arrival-rate">
          <NumericInput
            id="arrival-rate"
            value={borderConfig.arrival_rate}
            onValueChange={(value) => handleBorderConfigChange('arrival_rate', value)}
            min={0}
            stepSize={0.1}
          />
        </FormGroup>

        <FormGroup label="Service Rates" labelFor="service-rates">
          {borderConfig.service_rates.map((rate, index) => (
            <NumericInput
              key={index}
              value={rate}
              onValueChange={(value) => handleServiceRatesChange(index, value)}
              placeholder={`Node ${index + 1}`}
              min={0}
              stepSize={0.1}
              style={{ marginRight: '10px', width: '80px' }}
            />
          ))}
        </FormGroup>

        <FormGroup label="Queue Assignment" labelFor="queue-assignment">
          <HTMLSelect
            id="queue-assignment"
            value={borderConfig.queue_assignment}
            onChange={(e) => handleBorderConfigChange('queue_assignment', e.target.value as any)}
            options={[
              { label: 'Shortest', value: 'shortest' },
              { label: 'Random', value: 'random' },
              { label: 'Round Robin', value: 'round_robin' }
            ]}
          />
        </FormGroup>

        <FormGroup label="Safe Distance" labelFor="safe-distance">
          <NumericInput
            id="safe-distance"
            value={borderConfig.safe_distance}
            onValueChange={(value) => handleBorderConfigChange('safe_distance', value)}
            min={0}
            stepSize={0.1}
          />
        </FormGroup>

        <FormGroup label="Max Queue Length" labelFor="max-queue-length">
          <NumericInput
            id="max-queue-length"
            value={borderConfig.max_queue_length}
            onValueChange={(value) => handleBorderConfigChange('max_queue_length', value)}
            min={1}
          />
        </FormGroup>
      </Card>

      <Divider />

      <Card>
        <H3>Simulation Configuration</H3>
        <FormGroup label="Max Simulation Time (seconds)" labelFor="max-time">
          <NumericInput
            id="max-time"
            value={simulationConfig.max_simulation_time}
            onValueChange={(value) => handleSimulationConfigChange('max_simulation_time', value)}
            min={1}
          />
        </FormGroup>

        <FormGroup label="Time Factor" labelFor="time-factor">
          <NumericInput
            id="time-factor"
            value={simulationConfig.time_factor}
            onValueChange={(value) => handleSimulationConfigChange('time_factor', value)}
            min={0.1}
            stepSize={0.1}
          />
        </FormGroup>

        <Checkbox
          checked={simulationConfig.enable_telemetry}
          onChange={(e) => handleSimulationConfigChange('enable_telemetry', (e.target as HTMLInputElement).checked)}
        >
          Enable Telemetry
        </Checkbox>

        <Checkbox
          checked={simulationConfig.enable_position_tracking}
          onChange={(e) => handleSimulationConfigChange('enable_position_tracking', (e.target as HTMLInputElement).checked)}
        >
          Enable Position Tracking
        </Checkbox>
      </Card>

      <Divider />

      <Card>
        <H3>Phone Configuration (Optional)</H3>
        <Button
          onClick={() => setPhoneConfig(phoneConfig ? undefined : {
            sampling_rate: 10.0,
            gps_noise: { horizontal_accuracy: 5.0, vertical_accuracy: 10.0 },
            accelerometer_noise: 0.1,
            gyro_noise: 0.01,
            device_orientation: 'portrait'
          })}
        >
          {phoneConfig ? 'Remove Phone Config' : 'Add Phone Config'}
        </Button>

        {phoneConfig && (
          <>
            <FormGroup label="Sampling Rate" labelFor="sampling-rate">
              <NumericInput
                id="sampling-rate"
                value={phoneConfig.sampling_rate}
                onValueChange={(value) => handlePhoneConfigChange('sampling_rate', value)}
                min={0}
                stepSize={0.1}
              />
            </FormGroup>

            <FormGroup label="GPS Horizontal Accuracy" labelFor="gps-h-acc">
              <NumericInput
                id="gps-h-acc"
                value={phoneConfig.gps_noise.horizontal_accuracy}
                onValueChange={(value) => handlePhoneConfigChange('gps_noise', { ...phoneConfig.gps_noise, horizontal_accuracy: value })}
                min={0}
                stepSize={0.1}
              />
            </FormGroup>

            <FormGroup label="GPS Vertical Accuracy" labelFor="gps-v-acc">
              <NumericInput
                id="gps-v-acc"
                value={phoneConfig.gps_noise.vertical_accuracy}
                onValueChange={(value) => handlePhoneConfigChange('gps_noise', { ...phoneConfig.gps_noise, vertical_accuracy: value })}
                min={0}
                stepSize={0.1}
              />
            </FormGroup>

            <FormGroup label="Accelerometer Noise" labelFor="accel-noise">
              <NumericInput
                id="accel-noise"
                value={phoneConfig.accelerometer_noise}
                onValueChange={(value) => handlePhoneConfigChange('accelerometer_noise', value)}
                min={0}
                stepSize={0.01}
              />
            </FormGroup>

            <FormGroup label="Gyro Noise" labelFor="gyro-noise">
              <NumericInput
                id="gyro-noise"
                value={phoneConfig.gyro_noise}
                onValueChange={(value) => handlePhoneConfigChange('gyro_noise', value)}
                min={0}
                stepSize={0.01}
              />
            </FormGroup>

            <FormGroup label="Device Orientation" labelFor="orientation">
              <HTMLSelect
                id="orientation"
                value={phoneConfig.device_orientation}
                onChange={(e) => handlePhoneConfigChange('device_orientation', e.target.value as 'portrait' | 'landscape')}
                options={[
                  { label: 'Portrait', value: 'portrait' },
                  { label: 'Landscape', value: 'landscape' }
                ]}
              />
            </FormGroup>
          </>
        )}
      </Card>
    </div>
  );
};

export default ConfigurePanel;