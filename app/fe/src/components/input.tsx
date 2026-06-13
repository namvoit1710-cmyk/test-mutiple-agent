import React from 'react';
import './input.css';

interface InputProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  type?: string;
  className?: string;
  id?: string;
  name?: string;
}

const Input: React.FC<InputProps> = ({
  value = '',
  onChange,
  placeholder = '',
  disabled = false,
  type = 'text',
  className = '',
  id,
  name,
}) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.value);
  };

  return (
    <input
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      type={type}
      className={`input ${className}`}
      id={id}
      name={name}
    />
  );
};

export default Input;
