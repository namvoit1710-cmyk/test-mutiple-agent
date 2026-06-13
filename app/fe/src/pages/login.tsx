import React from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useAuth } from '../lib/auth-context';
import { PasswordControl } from '../components/password-control';
import './login.css';

interface LoginFormInputs {
  email: string;
  password: string;
}

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { register, handleSubmit, control, formState: { errors } } = useForm<LoginFormInputs>();

  const onSubmit = (data: LoginFormInputs) => {
    login(data.email, data.password);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h2 className="login-card__title">Login</h2>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input 
              id="email"
              type="email" 
              {...register("email", { 
                required: "Email is required", 
                pattern: { value: /^\S+@\S+$/i, message: "Invalid email format" } 
              })} 
            />
            {errors.email && <span className="error-message">{errors.email.message}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <Controller
              name="password"
              control={control}
              rules={{ required: "Password is required" }}
              render={({ field }) => (
                <PasswordControl 
                  id="password"
                  value={field.value} 
                  onChange={field.onChange} 
                />
              )}
            />
            {errors.password && <span className="error-message">{errors.password.message}</span>}
          </div>
          <button type="submit" className="login-submit">Sign In</button>
        </form>
      </div>
    </div>
  );
};
