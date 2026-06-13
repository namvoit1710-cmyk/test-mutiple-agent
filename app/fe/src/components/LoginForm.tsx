import React from 'react';

const LoginForm: React.FC = () => {
  return (
    <div className="login-container">
      <form className="login-form">
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          <input type="text" id="username" name="username" />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input type="password" id="password" name="password" />
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default LoginForm;
