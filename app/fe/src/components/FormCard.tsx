
import React from 'react';

interface FormCardProps {
  children: React.ReactNode;
}

const FormCard: React.FC<FormCardProps> = ({ children }) => {
  return (
    <div className="p-8 bg-white rounded-lg shadow-md">
      {children}
    </div>
  );
};

export default FormCard;
