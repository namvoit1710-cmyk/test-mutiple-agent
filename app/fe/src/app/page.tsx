
import React from 'react';
import MainContainer from '../components/MainContainer';
import FormCard from '../components/FormCard';
import EmailInput from '../components/EmailInput';
import PasswordInput from '../components/PasswordInput';
import SubmitButton from '../components/ui/SubmitButton';

export default function LoginPage() {
  return (
    <MainContainer>
      <FormCard>
        <h1 className="text-2xl font-bold mb-6 text-center">Login</h1>
        <form className="space-y-4">
          <EmailInput label="Email Address" placeholder="Enter your email" />
          <PasswordInput label="Password" placeholder="Enter your password" />
          <SubmitButton>Login</SubmitButton>
        </form>
      </FormCard>
    </MainContainer>
  );
}
