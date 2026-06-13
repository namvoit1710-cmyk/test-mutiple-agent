import React, { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';

interface AuthRouteProps {
  children: ReactNode;
}

export const AuthRoute = ({ children }: AuthRouteProps) => {
  const { isAuthenticated } = useAuth();

  return isAuthenticated ? <Navigate to="/home" replace /> : <>{children}</>;
};
