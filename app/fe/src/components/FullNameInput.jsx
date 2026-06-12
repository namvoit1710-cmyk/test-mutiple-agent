import React, { useState } from 'react';

const VALIDATION_REGEX = /^[a-zA-Z\s]*$/;
const MIN_LENGTH = 2;
const MAX_LENGTH = 50;

const FullNameInput = ({ label, placeholder, value, onChange, onValidationChange }) => {
  const [error, setError] = useState('');

  const validateInput = (inputValue) => {
    if (!inputValue) {
      setError('Full name is required.');
      onValidationChange(false);
      return false;
    }
    if (inputValue.length < MIN_LENGTH || inputValue.length > MAX_LENGTH) {
      setError(`Full name must be between ${MIN_LENGTH} and ${MAX_LENGTH} characters.`);
      onValidationChange(false);
      return false;
    }
    if (!VALIDATION_REGEX.test(inputValue)) {
      setError('Full name can only contain letters and spaces.');
      onValidationChange(false);
      return false;
    }
    setError('');
    onValidationChange(true);
    return true;
  };

  const handleChange = (event) => {
    const newValue = event.target.value;
    onChange(newValue);
    validateInput(newValue);
  };

  const handleBlur = () => {
    validateInput(value);
  };

  return (
    <div>
      <label>{label}</label>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        style={{ borderColor: error ? 'red' : 'initial' }} // Indicate error with border color
      />
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
};

export default FullNameInput;
