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
  value = "",
  onChange,
  placeholder = "",
  disabled = false,
  type = "text",
  className = "",
  id,
  name,
}) => {
  return (
    <input
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
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
