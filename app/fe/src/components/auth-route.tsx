import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

interface AuthRouteProps {
  isAuthenticated: boolean;
  children?: React.ReactNode;
}

const AuthRoute: React.FC<AuthRouteProps> = ({ isAuthenticated, children }) => {
  const location = useLocation();

  if (isAuthenticated) {
    // Redirect them to the /home page if they are already authenticated
    return <Navigate to="/home" state={{ from: location }} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};

export default AuthRoute;
