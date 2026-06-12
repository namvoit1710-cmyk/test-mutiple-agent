import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import HomePage from '../pages/HomePage';
import AuthGuard from '../guards/AuthGuard'; // Corrected path
import PrivateRoute from '../guards/PrivateRoute'; // Corrected path

const AppRoutes: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<AuthGuard><LoginPage /></AuthGuard>} />
        <Route path="/home" element={<PrivateRoute><HomePage /></PrivateRoute>} />
        {/* Other routes */}
      </Routes>
    </Router>
  );
};

export default AppRoutes;
