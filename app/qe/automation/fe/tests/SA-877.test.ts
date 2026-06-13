import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Input } from '../../../../fe/src/components/input'; // Relative path to the component

describe('SA-877 [FE] task-2', () => {
  // TC-001: Renders an input element with default type "text" and empty value.
  it('TC-001: Renders an input element with default type "text" and empty value', () => {
    render(<Input />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toBeInTheDocument();
    expect(inputElement).toHaveAttribute('type', 'text');
    expect(inputElement).toHaveValue('');
  });

  // TC-002: Renders an input element with the ".input" class applied.
  it('TC-002: Renders an input element with the ".input" class applied', () => {
    render(<Input />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveClass('input');
  });

  // TC-003: Renders with a provided `value`.
  it('TC-003: Renders with a provided `value`', () => {
    render(<Input value="test" />);
    const inputElement = screen.getByDisplayValue('test');
    expect(inputElement).toBeInTheDocument();
  });

  // TC-004: Renders with an empty `value`.
  it('TC-004: Renders with an empty `value`', () => {
    render(<Input value="" />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveValue('');
  });

  // TC-005: Calls `onChange` with the new value when input changes.
  it('TC-005: Calls `onChange` with the new value when input changes', () => {
    const mockOnChange = vi.fn();
    render(<Input onChange={mockOnChange} />);
    const inputElement = screen.getByRole('textbox');
    fireEvent.change(inputElement, { target: { value: 'new value' } });
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith('new value');
  });

  // TC-006: Renders with a provided `placeholder`.
  it('TC-006: Renders with a provided `placeholder`', () => {
    render(<Input placeholder="Enter text" />);
    const inputElement = screen.getByPlaceholderText('Enter text');
    expect(inputElement).toBeInTheDocument();
  });

  // TC-007: Renders without a `placeholder` when not provided.
  it('TC-007: Renders without a `placeholder` when not provided', () => {
    render(<Input />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).not.toHaveAttribute('placeholder');
  });

  // TC-008: Renders a disabled input when `disabled` is true.
  it('TC-008: Renders a disabled input when `disabled` is true', () => {
    render(<Input disabled={true} />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toBeDisabled();
  });

  // TC-009: Renders an enabled input when `disabled` is false.
  it('TC-009: Renders an enabled input when `disabled` is false', () => {
    render(<Input disabled={false} />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toBeEnabled();
  });

  // TC-010: Renders with a provided `type` (e.g., "password").
  it('TC-010: Renders with a provided `type` (e.g., "password")', () => {
    render(<Input type="password" />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveAttribute('type', 'password');
  });

  // TC-011: Renders with default `type` "text" when not provided.
  it('TC-011: Renders with default `type` "text" when not provided', () => {
    render(<Input />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveAttribute('type', 'text');
  });

  // TC-012: Applies an additional `className`.
  it('TC-012: Applies an additional `className`', () => {
    render(<Input className="custom-class" />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveClass('input');
    expect(inputElement).toHaveClass('custom-class');
  });

  // TC-013: Renders with a provided `id`.
  it('TC-013: Renders with a provided `id`', () => {
    render(<Input id="my-input" />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveAttribute('id', 'my-input');
  });

  // TC-014: Renders with a provided `name`.
  it('TC-014: Renders with a provided `name`', () => {
    render(<Input name="my-field" />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toHaveAttribute('name', 'my-field');
  });
});
