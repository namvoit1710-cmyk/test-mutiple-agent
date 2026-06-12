import React from 'react';

interface PasswordInputProps {
  label: string;
  placeholder: string;
  required?: boolean;
}

const PasswordInput: React.FC<PasswordInputProps> = ({ label, placeholder, required }) => {
  return (
    <div>
      <label htmlFor="password">{label}</label>
      <input
        type="password"
        id="password"
        name="password"
        placeholder={placeholder}
        required={required}
      />
    </div>
  );
};

export default PasswordInput;
