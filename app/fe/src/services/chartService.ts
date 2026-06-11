
interface Chart {
  id: string;
  type: string;
  config: ChartConfig;
}

let mockCharts: Chart[] = [
  { id: 'chart-abc', type: 'BAR', config: { type: 'BAR', title: 'Monthly Sales', data: [100, 200, 150] } },
  { id: 'chart-xyz', type: 'LINE', config: { type: 'LINE', title: 'Daily Visitors', data: [50, 70, 60, 90] } },
];

export const getChart = async (id: string): Promise<Chart | undefined> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockCharts.find(chart => chart.id === id));
    }, 300);
  });
};

interface ChartConfig {
  type: string;
  [key: string]: any; // Allows for arbitrary configuration properties
}

interface ChartCreationResponse {
  id: string;
  message: string;
}

export const createChart = async (chartConfig: ChartConfig): Promise<ChartCreationResponse> => {
  console.log('Simulating API call to create chart with config:', chartConfig);
  return new Promise((resolve) => {
    setTimeout(() => {
      const newChartId = `chart-${Math.random().toString(36).substr(2, 9)}`;
      resolve({
        id: newChartId,
        message: `Chart of type ${chartConfig.type} created successfully with ID: ${newChartId}`,
      });
    }, 1000);
  });
};
