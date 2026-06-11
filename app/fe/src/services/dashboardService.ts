
interface Dashboard {
  id: string;
  title: string;
  requiredRoles: string[];
  layout: string; // e.g., "2-column", "3-row"
}

let mockDashboards: Dashboard[] = [
  { id: 'dashboard-1', title: 'Sales Dashboard', requiredRoles: ['admin', 'sales'], layout: '2-column' },
  { id: 'dashboard-2', title: 'Marketing Dashboard', requiredRoles: ['admin', 'marketing'], layout: '3-row' },
];

export const getDashboard = async (id: string): Promise<Dashboard | undefined> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockDashboards.find(dashboard => dashboard.id === id));
    }, 300);
  });
};

interface ChartAssignment {
  slotId: string;
  chartId: string | null;
}

// This is a mock in-memory store for chart assignments.
// In a real application, this would interact with a backend API.
let mockChartAssignments: ChartAssignment[] = [
  { slotId: 'slot-1', chartId: 'chart-abc' },
  { slotId: 'slot-2', chartId: null },
  { slotId: 'slot-3', chartId: 'chart-xyz' },
];

export const updateChartAssignment = async (slotId: string, newChartId: string | null): Promise<ChartAssignment[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const index = mockChartAssignments.findIndex(assignment => assignment.slotId === slotId);
      if (index !== -1) {
        mockChartAssignments[index] = { ...mockChartAssignments[index], chartId: newChartId };
      } else {
        mockChartAssignments.push({ slotId, chartId: newChartId });
      }
      console.log(`Updated assignment for slot ${slotId}: ${newChartId}`);
      resolve(mockChartAssignments);
    }, 500);
  });
};

export const deleteChartAssignment = async (slotId: string): Promise<ChartAssignment[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const index = mockChartAssignments.findIndex(assignment => assignment.slotId === slotId);
      if (index !== -1) {
        mockChartAssignments[index] = { ...mockChartAssignments[index], chartId: null };
      }
      console.log(`Deleted assignment for slot ${slotId}`);
      resolve(mockChartAssignments);
    }, 500);
  });
};

export const getChartAssignments = async (): Promise<ChartAssignment[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockChartAssignments);
    }, 300);
  });
};
