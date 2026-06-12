import React from 'react';

interface SubmitButtonProps {
  children: React.ReactNode;
}

const SubmitButton: React.FC<SubmitButtonProps> = ({ children }) => {
  return (
    <button type="submit" className="submit-button">
      {children}
    </button>
  );
};

export default SubmitButton;
