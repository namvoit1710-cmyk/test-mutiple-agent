import React from 'react';
import AppRoutes from './routes'; // Assuming routes are defined here

const App: React.FC = () => {
  console.log('App component rendered');
  return (
    <div className="App">
      <AppRoutes />
    </div>
  );
};

export default App;
