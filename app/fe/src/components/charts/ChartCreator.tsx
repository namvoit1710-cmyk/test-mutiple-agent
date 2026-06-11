
import React, { useState } from 'react';
import ChartTypeSelection from './ChartTypeSelection';
import ChartConfigurationForms from './ChartConfigurationForms';
import { createChart } from '../../services/chartService';

// Simple Spinner Component (Duplicated for now, ideally would be shared)
const Spinner: React.FC = () => (
  <div style={{
    border: '4px solid rgba(0, 0, 0, .1)',
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    borderLeftColor: '#09f',
    animation: 'spin 1s ease infinite',
    display: 'inline-block',
    verticalAlign: 'middle',
    marginLeft: '10px'
  }}></div>
);

// Basic CSS for the spin animation (could be in a separate CSS file)
const styleSheet = document.styleSheets[0];
const keyframes = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
if (styleSheet) {
  styleSheet.insertRule(keyframes, styleSheet.cssRules.length);
}

const ChartCreator: React.FC = () => {
  const [selectedChartType, setSelectedChartType] = useState<string | null>(null);
  const [chartConfig, setChartConfig] = useState<any>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [createdChartId, setCreatedChartId] = useState<string | null>(null);

  const handleSelectChartType = (type: string) => {
    setSelectedChartType(type);
    setChartConfig({ type }); // Initialize config with type
    setError(null); // Clear any previous errors
  };

  const handleConfigChange = (newConfig: any) => {
    setChartConfig((prevConfig: any) => ({ ...prevConfig, ...newConfig }));
  };

  const handleSubmit = async () => {
    if (!selectedChartType) {
      setError('Please select a chart type before creating.');
      return;
    }

    setLoading(true);
    setError(null);
    setCreatedChartId(null);
    try {
      const response = await createChart(chartConfig);
      setCreatedChartId(response.id);
      // Optionally reset form or navigate
    } catch (err) {
      setError(`Error creating chart: ${err instanceof Error ? err.message : String(err)}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px', maxWidth: '600px', margin: '20px auto', boxShadow: '0 2px 4px rgba(0,0,0,.05)' }}>
      <h2>Create New Chart</h2>
      {error && <div style={{ color: 'red', marginBottom: '15px' }}>Error: {error}</div>}
      <ChartTypeSelection
        onSelectChartType={handleSelectChartType}
        selectedChartType={selectedChartType}
      />
      {selectedChartType && (
        <ChartConfigurationForms
          chartType={selectedChartType}
          onConfigChange={handleConfigChange}
        />
      )}
      <button onClick={handleSubmit} disabled={!selectedChartType || loading}
        style={{
          padding: '10px 20px',
          borderRadius: '5px',
          border: 'none',
          backgroundColor: '#28a745',
          color: 'white',
          cursor: 'pointer',
          marginTop: '20px',
          opacity: (!selectedChartType || loading) ? 0.6 : 1
        }}
      >
        {loading ? 'Creating...' : 'Create Chart'}
        {loading && <Spinner />}
      </button>
      {createdChartId && <p style={{ color: 'green', marginTop: '15px' }}>Chart created successfully! ID: {createdChartId}</p>}
    </div>
  );
};

export default ChartCreator;
