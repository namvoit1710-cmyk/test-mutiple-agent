import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/home';
import LoginPage from './pages/login';
import PrivateRoute from './components/private-route';
import AuthRoute from './components/auth-route';
import { AuthProvider, useAuth } from './lib/auth-context';

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthRoute isAuthenticated={isAuthenticated}><LoginPage /></AuthRoute>} />
        <Route path="/home" element={<PrivateRoute isAuthenticated={isAuthenticated}><HomePage /></PrivateRoute>} />
        {/* Add other routes here */}
        <Route path="*" element={<div>Not Found</div>} />
      </Routes>
    </BrowserRouter>
  );
}

const RootApp = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default RootApp;

