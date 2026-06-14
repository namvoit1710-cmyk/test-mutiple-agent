import React from 'react';
import { useAuth } from '../lib/auth-context';
import { APP_SLOGAN } from '../lib/auth-constants';
import './home.css';

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="home-page">
      <div className="blob-tr" />
      <div className="blob-bl" />
      <div className="home-content">
        <h1 className="welcome-text">Welcome, {user?.email}</h1>
        <p className="slogan-text">{APP_SLOGAN}</p>
        <button className="logout-button" onClick={logout}>Logout</button>
      </div>
    </div>
  );
};
