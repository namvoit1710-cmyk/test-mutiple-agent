
import React from "react";
import './HomePage.css'; // Assuming a CSS file for styles

const HomePage = () => {
  return (
    <div className="home-page-container" style={{ fontFamily: '"Inter", sans-serif', textAlign: 'center', color: '#333' }}>
      <h1 className="main-heading" style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Welcome to Our Platform</h1>
      <p className="subheading" style={{ fontSize: '1.2rem', marginBottom: '2rem', color: '#555' }}>Discover amazing features and more.</p>
      <button className="cta-button" style={{ padding: '0.8rem 1.5rem', fontSize: '1rem', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>Get Started</button>
    </div>
  );
};

export default HomePage;
