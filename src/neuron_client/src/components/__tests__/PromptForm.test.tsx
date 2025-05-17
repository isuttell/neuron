import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PromptForm } from "../PromptForm";
import { Prompt } from "../../slices/promptsSlice";

describe("PromptForm", () => {
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  const mockPrompt: Prompt = {
    id: "123",
    name: "Test Prompt",
    text: "This is a test prompt",
    personality_id: "456",
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders empty form correctly when no prompt is provided", () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/text/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create prompt/i })).toBeInTheDocument();

    // Inputs should be empty
    expect(screen.getByLabelText(/name/i)).toHaveValue("");
    expect(screen.getByLabelText(/text/i)).toHaveValue("");
  });

  it("renders form with existing prompt data when prompt is provided", () => {
    render(<PromptForm prompt={mockPrompt} onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue(mockPrompt.name);
    expect(screen.getByLabelText(/text/i)).toHaveValue(mockPrompt.text);
    expect(screen.getByRole("button", { name: /update prompt/i })).toBeInTheDocument();
  });

  it("handles input changes correctly", async () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const nameInput = screen.getByLabelText(/name/i);
    const textInput = screen.getByLabelText(/text/i);

    await userEvent.type(nameInput, "New Prompt");
    await userEvent.type(textInput, "New prompt text");

    expect(nameInput).toHaveValue("New Prompt");
    expect(textInput).toHaveValue("New prompt text");
  });

  it("calls onSubmit with correct values when form is submitted", async () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const nameInput = screen.getByLabelText(/name/i);
    const textInput = screen.getByLabelText(/text/i);
    const submitButton = screen.getByRole("button", { name: /create prompt/i });

    await userEvent.type(nameInput, "New Prompt");
    await userEvent.type(textInput, "New prompt text");
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith({
      name: "New Prompt",
      text: "New prompt text",
      personalityId: undefined,
    });
  });

  it("calls onSubmit with correct values when form with existing prompt is submitted", async () => {
    render(<PromptForm prompt={mockPrompt} onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const nameInput = screen.getByLabelText(/name/i);
    const textInput = screen.getByLabelText(/text/i);
    const submitButton = screen.getByRole("button", { name: /update prompt/i });

    // Clear and type new values
    await userEvent.clear(nameInput);
    await userEvent.clear(textInput);
    await userEvent.type(nameInput, "Updated Prompt");
    await userEvent.type(textInput, "Updated text");
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith({
      name: "Updated Prompt",
      text: "Updated text",
      personalityId: mockPrompt.personality_id,
    });
  });

  it("prevents form submission when required fields are empty", async () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const submitButton = screen.getByRole("button", { name: /create prompt/i });
    fireEvent.click(submitButton);

    // Since we have the required attribute on inputs, the form submission will be prevented by the browser
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("calls onCancel when cancel button is clicked", () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it("disables submit button when disabled prop is true", () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} disabled={true} />);

    // In the component, only the submit button actually has the disabled attribute
    expect(screen.getByRole("button", { name: /create prompt/i })).toBeDisabled();

    // Cancel button should still be enabled
    expect(screen.getByRole("button", { name: /cancel/i })).not.toBeDisabled();
  });

  it("handles form submission via submit event", async () => {
    render(<PromptForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    const nameInput = screen.getByLabelText(/name/i);
    const textInput = screen.getByLabelText(/text/i);

    await userEvent.type(nameInput, "New Prompt");
    await userEvent.type(textInput, "New prompt text");

    // Get the form directly since it doesn't have a role
    const form = document.querySelector("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    expect(mockOnSubmit).toHaveBeenCalledWith({
      name: "New Prompt",
      text: "New prompt text",
      personalityId: undefined,
    });
  });
});
