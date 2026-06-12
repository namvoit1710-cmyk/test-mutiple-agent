import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getToken } from '../utils/auth'; // Assuming getToken is in utils/auth

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const location = useLocation();
  const token = getToken();

  console.log('PrivateRoute: Checking authentication status');

  if (!token) {
    // If the user is not authenticated, redirect them to the login page
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateRoute;
