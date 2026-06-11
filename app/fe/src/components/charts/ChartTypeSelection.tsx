
import React from 'react';

interface ChartTypeSelectionProps {
  onSelectChartType: (type: string) => void;
  selectedChartType: string | null;
}

const ChartTypeSelection: React.FC<ChartTypeSelectionProps> = ({ onSelectChartType, selectedChartType }) => {
  const chartTypes = ['BAR', 'LINE', 'PIE', 'TABLE', 'KPI'];

  return (
    <div>
      <h3>Select Chart Type</h3>
      <select onChange={(e) => onSelectChartType(e.target.value)} value={selectedChartType || ''}>
        <option value="">--Please choose an option--</option>
        {chartTypes.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>
    </div>
  );
};

export default ChartTypeSelection;
