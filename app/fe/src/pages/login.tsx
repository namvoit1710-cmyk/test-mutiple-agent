import React from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useAuth } from '../lib/auth-context';
import PasswordControl from '../components/password-control';
import './login.css';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = (data: any) => {
    login(data.email, data.password);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-card__title">Login</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <Controller
              name="email"
              control={control}
              rules={{
                required: 'Email is required',
                pattern: {
                  value: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/,
                  message: 'Invalid email address',
                },
              }}
              render={({ field }) => (
                <input
                  id="email"
                  type="email"
                  {...field}
                  className="login-form__input"
                />
              )}
            />
            {errors.email && (
              <p className="error-message">{errors.email.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <Controller
              name="password"
              control={control}
              rules={{ required: 'Password is required' }}
              render={({ field }) => (
                <PasswordControl
                  value={field.value}
                  onChange={field.onChange}
                  disabled={false}
                />
              )}
            />
            {errors.password && (
              <p className="error-message">{errors.password.message}</p>
            )}
          </div>

          <button type="submit" className="login-form__submit-button">
            Log In
          </button>
        </form>
      </div>
    </div>
  );
};
