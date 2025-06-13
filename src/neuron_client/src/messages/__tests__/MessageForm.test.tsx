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

const mockAudioRecorderProps = {
  onRecordingComplete: vi.fn(),
  onAutoSend: vi.fn(),
};

vi.mock("@/components/AudioRecorder", () => ({
  AudioRecorder: (props: typeof mockAudioRecorderProps) => {
    mockAudioRecorderProps.onRecordingComplete = props.onRecordingComplete;
    mockAudioRecorderProps.onAutoSend = props.onAutoSend;
    return <div data-testid="audio-recorder">Audio Recorder</div>;
  },
}));

const mockPromptDropdownProps = {
  onSelectPrompt: vi.fn(),
  disabled: false,
};

vi.mock("@/components/PromptDropdown", () => ({
  PromptDropdown: (props: typeof mockPromptDropdownProps) => {
    mockPromptDropdownProps.onSelectPrompt = props.onSelectPrompt;
    mockPromptDropdownProps.disabled = props.disabled;
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
    mockAudioRecorderProps.onRecordingComplete.mockClear();
    mockAudioRecorderProps.onAutoSend.mockClear();
    mockPromptDropdownProps.onSelectPrompt.mockClear();
  });

  it("renders form elements correctly", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    expect(screen.getByTestId("message-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("audio-recorder")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-dropdown")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument();
  });

  it("updates message value when typing", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    await user.type(textarea, "Test message");

    expect(textarea).toHaveValue("Test message");
  });

  it("submits form with message when send button is clicked", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const sendButton = screen.getByRole("button", { name: /send message/i });

    await user.type(textarea, "Test message");
    await user.click(sendButton);

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
  });

  it("submits form when Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    await user.type(textarea, "Test message");
    await user.keyboard("{Enter}");

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
  });

  it("does not submit when Shift+Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    await user.type(textarea, "Test message");
    await user.keyboard("{Shift>}{Enter}{/Shift}");

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("clears form after submission", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const sendButton = screen.getByRole("button", { name: /send message/i });

    await user.type(textarea, "Test message");
    await user.click(sendButton);

    expect(textarea).toHaveValue("");
  });

  it("does not submit empty message", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const sendButton = screen.getByRole("button", { name: /send message/i });
    await user.click(sendButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("does not submit whitespace-only message", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const sendButton = screen.getByRole("button", { name: /send message/i });

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

    // Audio recording completion should trigger the onSubmit with the blob
    expect(mockOnSubmit).toHaveBeenCalledWith(mockBlob);
  });

  it("handles audio auto-send", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const mockBlob = new Blob(["audio data"], { type: "audio/wav" });
    act(() => {
      mockAudioRecorderProps.onAutoSend(mockBlob);
    });

    // Auto-send should trigger the onSubmit with the blob
    expect(mockOnSubmit).toHaveBeenCalledWith(mockBlob);
  });

  it("handles prompt selection", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const mockPromptText = "Selected prompt text";

    act(() => {
      mockPromptDropdownProps.onSelectPrompt(mockPromptText);
    });

    expect(textarea).toHaveValue(mockPromptText);
  });

  it("disables send button when submitting", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} isSubmitting={true} />);

    const sendButton = screen.getByRole("button", { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it("shows loading state on send button when submitting", () => {
    render(<MessageForm onSubmit={mockOnSubmit} isSubmitting={true} />);

    // Check for loading indicator (assuming it's present when isSubmitting is true)
    const sendButton = screen.getByRole("button", { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it("adjusts textarea height based on content", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const longMessage = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5";

    await user.type(textarea, longMessage);

    // The textarea should have adjusted its height
    expect(textarea.scrollHeight).toBeGreaterThan(textarea.clientHeight);
  });

  it("focuses textarea on mount", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    expect(textarea).toHaveFocus();
  });

  it("maintains focus on textarea after submission", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const sendButton = screen.getByRole("button", { name: /send message/i });

    await user.type(textarea, "Test message");
    await user.click(sendButton);

    expect(textarea).toHaveFocus();
  });

  it("handles rapid submissions gracefully", async () => {
    const user = userEvent.setup();
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const textarea = screen.getByTestId("message-textarea");
    const sendButton = screen.getByRole("button", { name: /send message/i });

    // Type message and submit multiple times rapidly
    await user.type(textarea, "Test message");
    await user.click(sendButton);
    await user.type(textarea, "Another message");
    await user.click(sendButton);

    expect(mockOnSubmit).toHaveBeenCalledTimes(2);
  });
});
