
import React, { useEffect, useState } from 'react';
import DashboardSlot from '../components/Dashboard/DashboardSlot';
import { getChartAssignments, updateChartAssignment, deleteChartAssignment } from '../services/dashboardService';

// Simple Spinner Component
const Spinner: React.FC = () => (
  <div style={{
    border: '4px solid rgba(0, 0, 0, .1)',
    width: '36px',
    height: '36px',
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


interface ChartAssignment {
  slotId: string;
  chartId: string | null;
}

const DashboardPage: React.FC = () => {
  const [assignments, setAssignments] = useState<ChartAssignment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [editingSlotId, setEditingSlotId] = useState<string | null>(null);
  const [newChartId, setNewChartId] = useState<string>('');

  useEffect(() => {
    const fetchAssignments = async () => {
      try {
        const fetchedAssignments = await getChartAssignments();
        setAssignments(fetchedAssignments);
      } catch (err) {
        setError('Failed to load dashboard assignments.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAssignments();
  }, []);

  const handleEdit = (slotId: string) => {
    setEditingSlotId(slotId);
    const currentAssignment = assignments.find(assign => assign.slotId === slotId);
    setNewChartId(currentAssignment?.chartId || '');
  };

  const handleRemove = async (slotId: string) => {
    setLoading(true);
    setError(null);
    try {
      const updatedAssignments = await deleteChartAssignment(slotId);
      setAssignments(updatedAssignments);
    } catch (err) {
      setError('Failed to remove chart from slot.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEdit = async () => {
    if (editingSlotId) {
      setLoading(true);
      setError(null);
      try {
        const updatedAssignments = await updateChartAssignment(editingSlotId, newChartId || null);
        setAssignments(updatedAssignments);
        setEditingSlotId(null);
        setNewChartId('');
      } catch (err) {
        setError('Failed to update chart assignment.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingSlotId(null);
    setNewChartId('');
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <Spinner />
        <p>Loading charts and assignments...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '22px' }}>
      <h1>Dashboard Overview</h1>
      {error && <div style={{ color: 'red', marginBottom: '15px' }}>Error: {error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px', marginTop: '20px' }}>
        {assignments.map((assignment) => (
          <DashboardSlot
            key={assignment.slotId}
            slotId={assignment.slotId}
            chartId={assignment.chartId}
            onEdit={handleEdit}
            onRemove={handleRemove}
          />
        ))}
      </div>

      {editingSlotId && (
        <div style={{ border: '1px solid #ccc', padding: '15px', margin: '20px 0', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
          <h2>Edit Slot: {editingSlotId}</h2>
          <input
            type="text"
            placeholder="New Chart ID (leave empty to unassign)"
            value={newChartId}
            onChange={(e) => setNewChartId(e.target.value)}
            style={{ marginRight: '10px', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
          />
          <button onClick={handleSaveEdit} style={{ padding: '8px 15px', borderRadius: '4px', border: 'none', backgroundColor: '#007bff', color: 'white', cursor: 'pointer', marginRight: '5px' }}>Save</button>
          <button onClick={handleCancelEdit} style={{ padding: '8px 15px', borderRadius: '4px', border: '1px solid #ccc', backgroundColor: '#f0f0f0', cursor: 'pointer' }}>Cancel</button>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
