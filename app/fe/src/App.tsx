import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

// Assume these components exist for now
const HomePage = () => <div>Home Page</div>;
const LoginPage = () => <div>Login Page</div>;

// Mock auth utility
const getToken = () => {
  // In a real app, this would check local storage, cookies, etc.
  // For now, let's simulate being logged out.
  return null;
};

// Route Guard for protected pages
const PrivateRoute = ({ children }) => {
  const token = getToken();
  return token ? children : <Navigate to="/login" />;
};

// Route Guard for authentication pages (e.g., login, signup)
const AuthRoute = ({ children }) => {
  const token = getToken();
  return token ? <Navigate to="/home" /> : children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<AuthRoute><LoginPage /></AuthRoute>} />
        <Route path="/home" element={<PrivateRoute><HomePage /></PrivateRoute>} />
        <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} /> {/* Redirect root to home if authenticated */} 
      </Routes>
    </Router>
  );
}

export default App;
