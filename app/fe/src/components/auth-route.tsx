import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/auth-context';

export const AuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/home" replace /> : <>{children}</>;
};
