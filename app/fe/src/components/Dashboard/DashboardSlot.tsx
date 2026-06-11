
import React from 'react';

interface DashboardSlotProps {
  slotId: string;
  chartId: string | null;
  onEdit: (slotId: string) => void;
  onRemove: (slotId: string) => void;
}

const DashboardSlot: React.FC<DashboardSlotProps> = ({ slotId, chartId, onEdit, onRemove }) => {
  return (
    <div style={{ border: '1px solid black', padding: '10px', margin: '5px' }}>
      <h3>Slot: {slotId}</h3>
      {chartId ? (
        <div>
          <p>Chart Assigned: {chartId}</p>
          <button onClick={() => onEdit(slotId)}>Edit Assignment</button>
          <button onClick={() => onRemove(slotId)}>Remove Assignment</button>
        </div>
      ) : (
        <p>Empty Slot</p>
      )}
    </div>
  );
};

export default DashboardSlot;
