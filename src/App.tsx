import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/lib/auth-context';
import { PrivateRoute } from '@/components/private-route';
import { AuthRoute } from '@/components/auth-route';

// Placeholder pages - these will be created in later tasks
const HomePage = React.lazy(() => import('@/pages/home'));
const LoginPage = React.lazy(() => import('@/pages/login'));

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
          <Route path="/home" element={<PrivateRoute><HomePage /></PrivateRoute>} />
          <Route path="/login" element={<AuthRoute><LoginPage /></AuthRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
