import React from 'react';
import { useAuth } from '../lib/auth-context';
import { SLOGAN } from '../lib/auth-constants';
import './home.css';

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="home-page">
      <div className="home-page__blob-tr" />
      <div className="home-page__blob-bl" />
      <div className="home-page__content">
        <h1 className="home-page__greeting">Welcome, {user?.email}</h1>
        <p className="home-page__slogan">{SLOGAN}</p>
        <button className="home-page__logout" onClick={logout}>Logout</button>
      </div>
    </div>
  );
};
