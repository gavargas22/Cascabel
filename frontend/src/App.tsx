import React, { useState } from 'react';
import { Tabs, Tab, Card, H1 } from '@blueprintjs/core';
import ConfigurePanel from './components/ConfigurePanel';
import RunPanel from './components/RunPanel';
import ResultsPanel from './components/ResultsPanel';
import MapviewPanel from './components/MapviewPanel';
import { BorderCrossingConfig, SimulationConfig, PhoneConfig } from './services/api';
import './App.css';

function App() {
  const [selectedTabId, setSelectedTabId] = useState<string>('create');
  const [simulationId, setSimulationId] = useState<string | null>(null);
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

  const handleConfigChange = (configs: {
    borderConfig: BorderCrossingConfig;
    simulationConfig: SimulationConfig;
    phoneConfig?: PhoneConfig;
  }) => {
    setBorderConfig(configs.borderConfig);
    setSimulationConfig(configs.simulationConfig);
    setPhoneConfig(configs.phoneConfig);
  };

  const handleSimulationStart = (id: string) => {
    setSimulationId(id);
  };

  return (
    <div className="App">
      <Card className="app-header">
        <H1>Border Traffic Simulation Dashboard</H1>
      </Card>
      <Card className="app-content">
        <Tabs
          id="dashboard-tabs"
          selectedTabId={selectedTabId}
          onChange={(newTabId) => setSelectedTabId(newTabId as string)}
          large={true}
        >
          <Tab
            id="create"
            title="Create"
            panel={<div>Create Simulation Panel - Coming Soon</div>}
          />
          <Tab
            id="configure"
            title="Configure"
            panel={<ConfigurePanel onConfigChange={handleConfigChange} />}
          />
          <Tab
            id="run"
            title="Run"
            panel={
              <RunPanel
                borderConfig={borderConfig}
                simulationConfig={simulationConfig}
                phoneConfig={phoneConfig}
                onSimulationStart={handleSimulationStart}
                onViewMap={() => setSelectedTabId('mapview')}
              />
            }
          />
          <Tab
            id="results"
            title="Results"
            panel={<ResultsPanel simulationId={simulationId} />}
          />
          <Tab
            id="mapview"
            title="Mapview"
            disabled={!simulationId}
            panel={simulationId ? <MapviewPanel simulationId={simulationId} /> : <div>Please start a simulation first</div>}
          />
        </Tabs>
      </Card>
    </div>
  );
}

export default App;
