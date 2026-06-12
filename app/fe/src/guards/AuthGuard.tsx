import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { getToken } from '../utils/auth';

const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const isAuthenticated = getToken() !== null;

  console.log('AuthGuard: Checking authentication status', { isAuthenticated });

  if (isAuthenticated) {
    // Redirect authenticated users away from login page
    return <Navigate to="/home" state={{ from: location }} replace />;
  }

  // Allow access to login page if not authenticated
  return <Outlet />;
};

export default AuthGuard;
