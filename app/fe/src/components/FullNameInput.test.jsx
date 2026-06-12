import React from \'react\';
import { render, screen, fireEvent } from \'@testing-library/react\';
import \'@testing-library/jest-dom\';
import FullNameInput from \'./FullNameInput\';

describe(\'FullNameInput\', () => {
  const defaultProps = {
    label: \'Full Name\',
    placeholder: \'Enter your full name\',
    required: false,
    validationRules: {
      minLength: 2,
      maxLength: 50,
      pattern: /^[A-Za-z\s]+$/,
    },
    errorMessage: \'Invalid full name\',
  };

  test(\'renders label, input, and error message area\', () => {
    render(<FullNameInput {...defaultProps} />);
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter your full name/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid full name/i)).toBeInTheDocument(); // Initially visible or not, depending on implementation
  });

  test(\'handles onChange event\', () => {
    render(<FullNameInput {...defaultProps} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    const testValue = \'John Doe\';
    fireEvent.change(inputElement, { target: { value: testValue } });
    expect(inputElement).toHaveValue(testValue);
  });

  test(\'validates minLength\', () => {
    render(<FullNameInput {...defaultProps} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    const shortValue = \'J\';
    fireEvent.change(inputElement, { target: { value: shortValue } });
    fireEvent.blur(inputElement); // Trigger validation on blur

    // Assuming error message is displayed when invalid
    expect(screen.getByText(/Invalid full name/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid full name/i)).toHaveClass(\'error-message\'); // Example class
  });

  test(\'validates maxLength\', () => {
    render(<FullNameInput {...defaultProps} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    const longValue = \'a\'.repeat(51);
    fireEvent.change(inputElement, { target: { value: longValue } });
    fireEvent.blur(inputElement);

    expect(screen.getByText(/Invalid full name/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid full name/i)).toHaveClass(\'error-message\');
  });

  test(\'validates pattern (allowed characters)\', () => {
    render(<FullNameInput {...defaultProps} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    const invalidCharValue = \'John Doe!\';
    fireEvent.change(inputElement, { target: { value: invalidCharValue } });
    fireEvent.blur(inputElement);

    expect(screen.getByText(/Invalid full name/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid full name/i)).toHaveClass(\'error-message\');
  });

  test(\'does not show error message when input is valid\', () => {
    render(<FullNameInput {...defaultProps} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    const validValue = \'Jane Smith\';
    fireEvent.change(inputElement, { target: { value: validValue } });
    fireEvent.blur(inputElement);

    // Assuming error message is hidden or has a different class when valid
    // This test might need adjustment based on the actual implementation of error message visibility
    // For now, we check if the error message element exists but doesn't have the error class, or is not visible.
    // A more robust test would check for absence or a specific 'valid' class.
    const errorMessageElement = screen.getByText(/Invalid full name/i);
    // If the error message is conditionally rendered, this might fail if it's not rendered at all.
    // A better approach might be to check for the absence of an error class or a specific "valid" indicator.
    // For this example, we'll assume the message is always present but its styling changes.
    // If the error message is *removed* from the DOM when valid, this test would need to change to expect it not to be found.
    // expect(screen.queryByText(/Invalid full name/i)).not.toBeInTheDocument(); // Use this if error message is removed
    expect(errorMessageElement).toBeInTheDocument(); // Assuming it's always there but styled differently
    expect(errorMessageElement).not.toHaveClass(\'error-message\'); // Example: check it doesn't have the error class
  });

  test(\'handles required field validation\', () => {
    render(<FullNameInput {...defaultProps} required={true} />);
    const inputElement = screen.getByLabelText(/Full Name/i);
    fireEvent.change(inputElement, { target: { value: \'\' } });
    fireEvent.blur(inputElement);

    expect(screen.getByText(/Invalid full name/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid full name/i)).toHaveClass(\'error-message\');
  });
});
