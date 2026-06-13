import React from 'react';
import { useAuth } from '../lib/auth-context';
import { SLOGAN_TEXT } from '../lib/auth-constants';
import './home.css';

const HomePage: React.FC = () => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="home-page">
      <div className="home-page__content">
        <h1>Welcome, {user?.email}</h1>
        <p>{SLOGAN_TEXT}</p>
        <button className="home-page__logout-button" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </div>
  );
};

export default HomePage;
