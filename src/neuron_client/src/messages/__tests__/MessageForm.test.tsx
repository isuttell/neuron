import {
  act,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Mock } from "jest-mock";
import { useParams } from "react-router-dom";
import MessageForm from "../MessageForm";


// Mock dependencies
jest.mock("react-router-dom", () => ({
  useParams: jest.fn() as Mock<() => { threadId: string }>,
}));

const mockAudioRecorderProps = {
  onRecordingComplete: jest.fn(),
  onAutoSend: jest.fn(),
};

jest.mock("@/components/AudioRecorder", () => ({
  AudioRecorder: (props: typeof mockAudioRecorderProps) => {
    mockAudioRecorderProps.onRecordingComplete = props.onRecordingComplete;
    mockAudioRecorderProps.onAutoSend = props.onAutoSend;
    return <div data-testid="audio-recorder">Audio Recorder</div>;
  },
}));

const mockPromptDropdownProps = {
  onSelectPrompt: jest.fn(),
  disabled: false,
};

jest.mock("@/components/PromptDropdown", () => ({
  PromptDropdown: (props: typeof mockPromptDropdownProps) => {
    mockPromptDropdownProps.onSelectPrompt = props.onSelectPrompt;
    mockPromptDropdownProps.disabled = props.disabled;
    return <div data-testid="prompt-dropdown">Prompt Dropdown</div>;
  },
}));

describe("MessageForm", () => {
  const mockOnSubmit = jest.fn();
  const mockThreadId = "123";

  beforeEach(() => {
    jest.clearAllMocks();
    (useParams as jest.MockedFunction<typeof useParams>).mockReturnValue({
      threadId: mockThreadId,
    });
  });

  it("renders form elements correctly", () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    expect(
      screen.getByPlaceholderText("Type your message here...")
    ).toBeInTheDocument();
    expect(screen.getByTestId("submit-button")).toBeInTheDocument();
    expect(screen.getByTestId("audio-recorder")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-dropdown")).toBeInTheDocument();
  });

  it("handles text input correctly", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");

    expect(input).toHaveValue("Test message");
  });

  it("handles form submission with text", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    const submitButton = screen.getByTestId("submit-button");

    await userEvent.type(input, "Test message");
    fireEvent.click(submitButton);

    // When onSubmit is provided, it should only call onSubmit
    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
    expect(input).toHaveValue("");
  });

  it("prevents submission with empty message and no file", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByTestId("submit-button");
    fireEvent.click(submitButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles file upload correctly", async () => {
    const mockOnFileAdd = jest.fn();
    render(<MessageForm onSubmit={mockOnSubmit} onFileAdd={mockOnFileAdd} />);

    const file = new File(["test"], "test.txt", { type: "text/plain" });
    const input = document.getElementById("file-upload") as HTMLInputElement;
    await userEvent.upload(input, file);

    const attachmentIndicator = screen.getByText(/file attached: test\.txt/i);
    expect(attachmentIndicator).toBeInTheDocument();
    expect(mockOnFileAdd).toHaveBeenCalledWith(file, false);
  });

  it("handles empty file selection", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = document.getElementById("file-upload") as HTMLInputElement;
    const event = {
      target: { files: null },
    } as unknown as React.ChangeEvent<HTMLInputElement>;
    fireEvent.change(input, event);

    expect(screen.queryByText(/file attached:/i)).not.toBeInTheDocument();
  });

  it("handles file removal", async () => {
    const mockOnFileRemove = jest.fn();
    render(<MessageForm onSubmit={mockOnSubmit} onFileRemove={mockOnFileRemove} />);

    const file = new File(["test"], "test.txt", { type: "text/plain" });
    const fileInput = document.getElementById(
      "file-upload"
    ) as HTMLInputElement;
    await userEvent.upload(fileInput, file);

    const removeButton = screen.getByLabelText("Remove attachment");
    fireEvent.click(removeButton);

    expect(screen.queryByText(/file attached:/i)).not.toBeInTheDocument();
    expect(mockOnFileRemove).toHaveBeenCalled();
  });

  it("handles Enter key submission", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message{enter}");

    // When onSubmit is provided, it should only call onSubmit
    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
  });

  it("shows loading state when isLoading is true", () => {
    render(<MessageForm onSubmit={mockOnSubmit} isLoading={true} />);

    const submitButton = screen.getByTestId("submit-button");
    expect(submitButton.querySelector("svg")).toHaveClass("animate-spin");
  });

  it("calls onSubmit with correct parameters", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
    expect(input).toHaveValue("");
  });

  it("respects disabled prop", () => {
    render(<MessageForm onSubmit={mockOnSubmit} disabled={true} />);

    expect(
      screen.getByPlaceholderText("Type your message here...")
    ).toBeDisabled();
    expect(screen.getByTestId("submit-button")).toBeDisabled();
  });

  it("applies custom className", () => {
    render(<MessageForm onSubmit={mockOnSubmit} className="custom-class" />);

    expect(document.querySelector("form")).toHaveClass("custom-class");
  });

  it("calls onSubmit regardless of threadId", async () => {
    (useParams as jest.Mock).mockReturnValue({ threadId: undefined });
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
  });

  it("calls onSubmit when form is submitted", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    const submitButton = screen.getByTestId("submit-button");

    await userEvent.type(input, "Test message");
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", undefined);
    expect(input).toHaveValue("");
  });

  it("handles audio recording completion", async () => {
    const mockOnFileAdd = jest.fn();
    render(<MessageForm onSubmit={mockOnSubmit} onFileAdd={mockOnFileAdd} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onRecordingComplete(blob);
    });

    const attachmentIndicator = screen.getByText(/audio recording attached/i);
    expect(attachmentIndicator).toBeInTheDocument();
    expect(mockOnFileAdd).toHaveBeenCalledWith(blob, true);
  });

  it("handles auto-send of audio recording", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    expect(mockOnSubmit).toHaveBeenCalledWith("", blob);
  });

  it("clears form state after auto-send", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    expect(mockOnSubmit).toHaveBeenCalledWith("Test message", blob);
    expect(input).toHaveValue("");
  });

  it("auto-send works regardless of threadId", async () => {
    (useParams as jest.Mock).mockReturnValue({ threadId: undefined });
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    expect(mockOnSubmit).toHaveBeenCalledWith("", blob);
  });

  it("allows shift+enter for newlines", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test{Shift>}{Enter}{/Shift}message");

    expect(input).toHaveValue("Test\nmessage");
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles prompt selection", async () => {
    render(<MessageForm onSubmit={mockOnSubmit} />);

    await act(async () => {
      mockPromptDropdownProps.onSelectPrompt("Selected prompt");
    });

    const input = screen.getByPlaceholderText("Type your message here...");
    expect(input).toHaveValue("Selected prompt");
  });

  it("disables prompt dropdown when form is disabled", () => {
    render(<MessageForm onSubmit={mockOnSubmit} disabled={true} />);
    expect(mockPromptDropdownProps.disabled).toBe(true);
  });
});
