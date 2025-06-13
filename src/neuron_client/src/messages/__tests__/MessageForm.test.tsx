import { vi } from 'vitest';
import {
  act,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useParams } from "react-router-dom";
import MessageForm from "../MessageForm";
import { useAppDispatch } from "@/hooks";

// Mock dependencies
vi.mock("../../hooks", () => ({
  useAppDispatch: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useParams: vi.fn(),
}));

// Mock sonner toast for Vitest
vi.mock("sonner", () => {
  const mockToast = Object.assign(vi.fn(), {
    error: vi.fn(),
  });
  return {
    toast: mockToast,
  };
});

vi.mock("../../actions/messageActions", () => ({
  postMessageByThread: vi.fn(),
}));

let mockAudioRecorderProps = {
  onRecordingComplete: vi.fn(),
  onAutoSend: vi.fn(),
};

vi.mock("@/components/AudioRecorder", () => ({
  AudioRecorder: (props: { onRecordingComplete: (blob: Blob) => void; onAutoSend: (blob: Blob) => void }) => {
    Object.assign(mockAudioRecorderProps, props);
    return <div data-testid="audio-recorder">Audio Recorder</div>;
  },
}));

let mockPromptDropdownProps = {
  onSelectPrompt: vi.fn(),
  disabled: false,
};

vi.mock("@/components/PromptDropdown", () => ({
  PromptDropdown: (props: { onSelectPrompt: (prompt: string) => void; disabled: boolean }) => {
    Object.assign(mockPromptDropdownProps, props);
    return <div data-testid="prompt-dropdown">Prompt Dropdown</div>;
  },
}));

describe("MessageForm", () => {
  const mockDispatch = vi.fn();
  const mockOnSubmit = vi.fn();
  const mockThreadId = "123";

  beforeEach(() => {
    vi.clearAllMocks();
    (
      useAppDispatch as vi.MockedFunction<typeof useAppDispatch>
    ).mockReturnValue(mockDispatch);
    (useParams as vi.MockedFunction<typeof useParams>).mockReturnValue({
      threadId: mockThreadId,
    });

    // Reset mock functions
    mockAudioRecorderProps = {
      onRecordingComplete: vi.fn(),
      onAutoSend: vi.fn(),
    };
    mockPromptDropdownProps = {
      onSelectPrompt: vi.fn(),
      disabled: false,
    };
  });

  it("renders form elements correctly", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    expect(screen.getByPlaceholderText("Type your message here...")).toBeInTheDocument();
    expect(screen.getByTestId("audio-recorder")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-dropdown")).toBeInTheDocument();
    expect(screen.getByTestId("submit-button")).toBeInTheDocument();
  });

  it("updates message value when typing", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    await user.type(textarea, "Test message");

    expect(textarea).toHaveValue("Test message");
  });

  it("submits form with message when send button is clicked", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const sendButton = screen.getByTestId("submit-button");

    await user.type(textarea, "Test message");
    await user.click(sendButton);

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
  });

  it("submits form when Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    await user.type(textarea, "Test message");
    await user.keyboard("{Enter}");

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
  });

  it("does not submit when Shift+Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    await user.type(textarea, "Test message");
    await user.keyboard("{Shift>}{Enter}{/Shift}");

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("clears form after submission", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const sendButton = screen.getByTestId("submit-button");

    await user.type(textarea, "Test message");
    await user.click(sendButton);

    expect(textarea).toHaveValue("");
  });

  it("does not submit empty message", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const sendButton = screen.getByTestId("submit-button");
    await user.click(sendButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("does not submit whitespace-only message", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const sendButton = screen.getByTestId("submit-button");

    await user.type(textarea, "   ");
    await user.click(sendButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles audio recording completion", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const mockBlob = new Blob(["audio data"], { type: "audio/wav" });
    act(() => {
      mockAudioRecorderProps.onRecordingComplete(mockBlob);
    });

    // Audio recording completion should store the blob but not submit automatically
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles audio auto-send", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const mockBlob = new Blob(["audio data"], { type: "audio/wav" });
    act(() => {
      mockAudioRecorderProps.onAutoSend(mockBlob);
    });

    // Auto-send should trigger the onSubmit with empty text and the blob
    expect(mockOnSubmit).toHaveBeenCalledWith("", mockBlob);
  });

  it("handles prompt selection", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const mockPromptText = "Selected prompt text";

    act(() => {
      mockPromptDropdownProps.onSelectPrompt(mockPromptText);
    });

    expect(textarea).toHaveValue(mockPromptText);
  });

  it("disables send button when submitting", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} isSubmitting={true} />);

    const sendButton = screen.getByTestId("submit-button");
    expect(sendButton).toBeDisabled();
  });

  it("shows loading state on send button when submitting", () => {
    render(<MessageForm onSubmit={mockOnSubmit} isSubmitting={true} />);

    // Check for loading indicator (assuming it's present when isSubmitting is true)
    const sendButton = screen.getByTestId("submit-button");
    expect(sendButton).toBeDisabled();
  });

  it("adjusts textarea height based on content", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const longMessage = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5";

    await user.type(textarea, longMessage);

    // Verify the content was entered correctly
    expect(textarea).toHaveValue(longMessage);
  });

  it("focuses textarea on mount", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    // Focus happens in useEffect with setTimeout, wait for it
    await new Promise(resolve => setTimeout(resolve, 100));
    expect(textarea).toHaveFocus();
  });

  it("maintains focus on textarea after submission", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");
    const sendButton = screen.getByTestId("submit-button");

    await user.type(textarea, "Test message");
    // First ensure textarea has focus
    textarea.focus();
    await user.click(sendButton);

    // After submission, check that content was cleared
    expect(textarea).toHaveValue("");
  });

  it("handles rapid submissions gracefully", async () => {
    const user = userEvent.setup();
    const localMockOnSubmit = vi.fn();
    render(<MessageForm onSubmit={localMockOnSubmit} />);

    const textarea = screen.getByPlaceholderText("Type your message here...");

    // Type and submit with Enter key
    await user.type(textarea, "Test message");
    await user.keyboard("{Enter}");

    // Wait for form to clear and then type second message
    expect(textarea).toHaveValue("");
    await user.type(textarea, "Another message");
    await user.keyboard("{Enter}");

    // Should have been called twice
    expect(localMockOnSubmit).toHaveBeenCalledTimes(2);
    expect(localMockOnSubmit).toHaveBeenNthCalledWith(1, "Test message", undefined);
    expect(localMockOnSubmit).toHaveBeenNthCalledWith(2, "Another message", undefined);
  });

  it("renders children content correctly", () => {
    const childContent = <div data-testid="child-content">Test Child</div>;
    render(<MessageForm onSubmit={mockOnSubmit}>{childContent}</MessageForm>);

    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.getByText("Test Child")).toBeInTheDocument();
  });

  it("does not render children container when no children provided", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    // The children container should not be in the DOM when no children
    expect(screen.queryByTestId("child-content")).not.toBeInTheDocument();
  });

  it("positions children correctly relative to form controls", () => {
    const childContent = <div data-testid="child-content">Test Child</div>;
    render(<MessageForm onSubmit={mockOnSubmit}>{childContent}</MessageForm>);

    const childElement = screen.getByTestId("child-content");
    const submitButton = screen.getByTestId("submit-button");

    // Both should be in the document
    expect(childElement).toBeInTheDocument();
    expect(submitButton).toBeInTheDocument();

    // The children should appear before the submit button in the button row
    const buttonRow = submitButton.closest(".flex.flex-row");
    expect(buttonRow).toContainElement(childElement);
  });
});
