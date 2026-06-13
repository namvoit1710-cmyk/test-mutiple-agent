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

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  return (
    <div className="login-page">
      <div className="login-card">
        <form className="login-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input 
              id="email" 
              type="email" 
              {...register("email", { required: true, pattern: emailRegex })} 
            />
            {errors.email && <span className="error-message">Valid email is required</span>}
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <Controller
              name="password"
              control={control}
              rules={{ required: true }}
              render={({ field }) => (
                <PasswordControl 
                  id="password"
                  value={field.value} 
                  onChange={field.onChange} 
                />
              )}
            />
            {errors.password && <span className="error-message">Password is required</span>}
          </div>
          <button type="submit" className="login-submit">Login</button>
        </form>
      </div>
    </div>
  );
};
