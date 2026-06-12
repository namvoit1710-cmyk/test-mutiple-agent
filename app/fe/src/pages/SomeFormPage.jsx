
import React, { useState } from 'react';
import FullNameInput from './FullNameInput';

const SomeFormPage = () => {
  const [fullName, setFullName] = useState('');
  const [isFullNameValid, setIsFullNameValid] = useState(false);

  const handleFullNameChange = (value) => {
    setFullName(value);
  };

  const handleFullNameValidationChange = (isValid) => {
    setIsFullNameValid(isValid);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    // Handle form submission logic here
    console.log('Form submitted with:', { fullName });
  };

  return (
    <div>
      <h1>User Form</h1>
      <form onSubmit={handleSubmit}>
        <FullNameInput
          label="Full Name"
          placeholder="Enter your full name"
          value={fullName}
          onChange={handleFullNameChange}
          onValidationChange={handleFullNameValidationChange}
        />
        {/* Other form elements would go here */}
        <button type="submit" disabled={!isFullNameValid}>
          Submit
        </button>
      </form>
    </div>
  );
};

export default SomeFormPage;
