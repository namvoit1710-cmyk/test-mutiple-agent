import React from 'react';

interface EmailInputProps {
  label: string;
  placeholder: string;
  required?: boolean;
}

const EmailInput: React.FC<EmailInputProps> = ({ label, placeholder, required }) => {
  return (
    <div>
      <label htmlFor="email">{label}</label>
      <input
        type="email"
        id="email"
        name="email"
        placeholder={placeholder}
        required={required}
      />
    </div>
  );
};

export default EmailInput;
