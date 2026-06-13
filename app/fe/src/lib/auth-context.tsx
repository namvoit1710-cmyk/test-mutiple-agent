import React, { createContext, useContext, useState, ReactNode } from 'react';
import { SLOGAN_TEXT } from './auth-constants';

interface User {
  email: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string, password: string) => void;
  logout: () => void;
  slogan: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);

  const login = (email: string, password: string) => {
    // In-memory authentication for now.
    // In a real app, this would involve API calls and token handling.
    if (email && password) { // Basic check, actual validation will be in login page
      setIsAuthenticated(true);
      setUser({ email });
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(null);
  };

  const slogan = SLOGAN_TEXT;

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, slogan }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
