import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  H3,
  Callout,
  Spinner,
  Text,
  Divider
} from '@blueprintjs/core';
import { api, SimulationStatus } from '../services/api';

interface ResultsPanelProps {
  simulationId: string | null;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ simulationId }) => {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (simulationId) {
      fetchResults();
    }
  }, [simulationId]);

  const fetchResults = async () => {
    if (!simulationId) return;
    setLoading(true);
    setError(null);
    try {
      const simulationStatus = await api.getSimulationStatus(simulationId);
      setStatus(simulationStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  };

  const downloadTelemetry = async () => {
    if (!simulationId) return;
    try {
      const response = await fetch(`http://localhost:8001/simulation/${simulationId}/telemetry`);
      if (!response.ok) {
        throw new Error('Failed to download telemetry');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `simulation_${simulationId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download telemetry');
    }
  };

  if (!simulationId) {
    return (
      <Card>
        <H3>Simulation Results</H3>
        <Text>No simulation results available. Run a simulation first.</Text>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <H3>Simulation Results</H3>
        <Spinner />
        <Text>Loading results...</Text>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <H3>Simulation Results</H3>
        <Callout intent="danger" title="Error">
          {error}
        </Callout>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card>
        <H3>Simulation Results</H3>
        <Text>No results data available.</Text>
      </Card>
    );
  }

  return (
    <div>
      <Card>
        <H3>Simulation Results</H3>
        <Text>Simulation ID: {simulationId}</Text>
        <br />
        <Text>Status: {status.status}</Text>
        <br />
        <Text>Final Time: {status.current_time.toFixed(1)}s</Text>
        <br />
        <Text>Total Arrivals: {status.total_arrivals}</Text>
        <br />
        <Text>Total Completions: {status.total_completions}</Text>
        <br />
        <Text>Throughput: {(status.total_completions / status.current_time * 3600).toFixed(2)} cars/hour</Text>
      </Card>

      <Divider />

      <Card>
        <H3>Telemetry Data</H3>
        <Text>Download the complete telemetry data as CSV for further analysis.</Text>
        <br />
        <Button
          intent="primary"
          onClick={downloadTelemetry}
          disabled={status.status !== 'completed'}
        >
          Download CSV
        </Button>
        {status.status !== 'completed' && (
          <Text>Download available when simulation is completed.</Text>
        )}
      </Card>

      {status.status === 'completed' && (
        <Callout intent="success" title="Simulation Completed">
          Results are ready for download and analysis.
        </Callout>
      )}

      {status.status === 'failed' && (
        <Callout intent="danger" title="Simulation Failed">
          {status.message || 'The simulation encountered an error.'}
        </Callout>
      )}
    </div>
  );
};

export default ResultsPanel;