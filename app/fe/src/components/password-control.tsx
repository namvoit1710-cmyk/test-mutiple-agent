import React, { forwardRef, useImperativeHandle, useRef } from 'react';

export interface PasswordControlRef {
  getValue: () => string;
  setValue: (value: string) => void;
  clear: () => void;
}

interface PasswordControlProps {
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  name?: string;
  autoComplete?: string;
}

const PasswordControl = forwardRef<PasswordControlRef, PasswordControlProps>(
  ({ placeholder, disabled, className, id, name, autoComplete }, ref) => {
    const inputRef = useRef<HTMLInputElement>(null);

    useImperativeHandle(ref, () => ({
      getValue: () => inputRef.current?.value || '',
      setValue: (value: string) => {
        if (inputRef.current) {
          inputRef.current.value = value;
        }
      },
      clear: () => {
        if (inputRef.current) {
          inputRef.current.value = '';
        }
      },
    }));

    return (
      <div className={`password-control ${className || ''}`}>
        <input
          type="password"
          ref={inputRef}
          placeholder={placeholder}
          disabled={disabled}
          id={id}
          name={name}
          autoComplete={autoComplete}
          className="password-control__input"
        />
        <button type="button" className="password-control__toggle">
          {/* SVG icons will go here in a later task */}
        </button>
      </div>
    );
  }
);

PasswordControl.displayName = 'PasswordControl';

export default PasswordControl;
