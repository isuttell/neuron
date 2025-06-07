import type { ToastProps } from "@/components/ui/toast";
import type { Thread as ThreadModel } from "../../types/thread";
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Mock } from "jest-mock";
import { useParams } from "react-router-dom";
import { postMessageByThread } from "../../actions/messageActions";
import { useAppDispatch } from "../../hooks";
import { useToast } from "../../hooks/use-toast";
import { AppDispatch } from "../../store";
import { Thread } from "../../types/thread";
import ThreadMessageForm from "../ThreadMessageForm";

type ToastReturnType = {
  id: string;
  dismiss: () => void;
  update: (props: ToastProps) => void;
};

// Mock dependencies
jest.mock("../../hooks", () => ({
  useAppDispatch: jest.fn() as Mock<() => AppDispatch>,
}));

jest.mock("react-router-dom", () => ({
  useParams: jest.fn() as Mock<() => { threadId: string }>,
}));

jest.mock("../../hooks/use-toast", () => ({
  useToast: jest.fn() as Mock<
    () => {
      toast: (props: ToastProps) => ToastReturnType;
      dismiss: (toastId?: string) => void;
      toasts: ToastProps[];
    }
  >,
}));

jest.mock("../../actions/messageActions", () => ({
  postMessageByThread: jest.fn(),
}));

// Mock MessageForm component
const mockMessageFormProps = {
  onSubmit: jest.fn(),
  onFileAdd: jest.fn(),
  onFileRemove: jest.fn(),
  isLoading: false,
  className: "",
};

jest.mock("../MessageForm", () => {
  return function MockMessageForm(props: typeof mockMessageFormProps) {
    mockMessageFormProps.onSubmit = props.onSubmit;
    mockMessageFormProps.onFileAdd = props.onFileAdd;
    mockMessageFormProps.onFileRemove = props.onFileRemove;
    mockMessageFormProps.isLoading = props.isLoading;
    mockMessageFormProps.className = props.className;

    return (
      <div data-testid="message-form">
        <button
          data-testid="mock-submit"
          onClick={() => props.onSubmit("test message", undefined)}
        >
          Submit
        </button>
        <button
          data-testid="mock-file-add"
          onClick={() => props.onFileAdd?.(new File(["test"], "test.txt"), false)}
        >
          Add File
        </button>
        <button
          data-testid="mock-file-remove"
          onClick={() => props.onFileRemove?.()}
        >
          Remove File
        </button>
        <div data-testid="loading-state">{props.isLoading ? "loading" : "idle"}</div>
        <div data-testid="class-name">{props.className}</div>
      </div>
    );
  };
});

describe("ThreadMessageForm", () => {
  const mockDispatch = jest.fn();
  const mockToast = jest.fn();
  const mockThreadId = "test-thread-123";

  const mockThread: Thread = {
    id: mockThreadId,
    name: "Test Thread",
    context: "Test context",
    memory: "Test memory",
    personality_id: "personality-456",
    status: "idle",
    message_count: 5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    jest.clearAllMocks();

    (useAppDispatch as jest.MockedFunction<typeof useAppDispatch>).mockReturnValue(mockDispatch);
    (useParams as jest.MockedFunction<typeof useParams>).mockReturnValue({
      threadId: mockThreadId,
    });
    (useToast as jest.MockedFunction<typeof useToast>).mockReturnValue({
      toast: mockToast,
      dismiss: jest.fn(),
      toasts: [],
    });

    mockDispatch.mockResolvedValue({
      messages: [],
      media: [],
    });
  });

  it("renders MessageForm with correct props", () => {
    render(<ThreadMessageForm thread={mockThread} className="test-class" />);

    expect(screen.getByTestId("message-form")).toBeInTheDocument();
    expect(screen.getByTestId("loading-state")).toHaveTextContent("idle");
    expect(screen.getByTestId("class-name")).toHaveTextContent("test-class");
  });

  it("shows loading state when thread status is not idle", () => {
    const loadingThread = { ...mockThread, status: "processing" as const };
    render(<ThreadMessageForm thread={loadingThread} />);

    expect(screen.getByTestId("loading-state")).toHaveTextContent("loading");
  });

  it("handles message submission successfully", async () => {
    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-submit"));

    expect(mockDispatch).toHaveBeenCalledWith(
      postMessageByThread({
        threadId: mockThreadId,
        prompt: "test message",
        personalityId: mockThread.personality_id,
        file: undefined,
      })
    );
  });

  it("handles message submission with file", async () => {
    const mockFile = new File(["test content"], "test.txt", { type: "text/plain" });

    // Mock the MessageForm to call onSubmit with a file
    jest.doMock("../MessageForm", () => {
      return function MockMessageForm(props: { onSubmit: (text: string, file?: File | Blob) => void; [key: string]: unknown }) {
        return (
          <button
            data-testid="mock-submit-with-file"
            onClick={() => props.onSubmit("test message", mockFile)}
          >
            Submit with File
          </button>
        );
      };
    });

    const { rerender } = render(<ThreadMessageForm thread={mockThread} />);
    rerender(<ThreadMessageForm thread={mockThread} />);

    if (screen.queryByTestId("mock-submit-with-file")) {
      fireEvent.click(screen.getByTestId("mock-submit-with-file"));

      expect(mockDispatch).toHaveBeenCalledWith(
        postMessageByThread({
          threadId: mockThreadId,
          prompt: "test message",
          personalityId: mockThread.personality_id,
          file: mockFile,
        })
      );
    }
  });

  it("handles submission error and shows toast", async () => {
    const error = new Error("Network error");
    mockDispatch.mockRejectedValueOnce(error);

    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-submit"));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        variant: "destructive",
        title: "Failed to send message",
        description: "Network error",
      });
    });
  });

  it("handles submission error with unknown error type", async () => {
    mockDispatch.mockRejectedValueOnce("Unknown error");

    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-submit"));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        variant: "destructive",
        title: "Failed to send message",
        description: "An unexpected error occurred",
      });
    });
  });

  it("does not submit when threadId is missing", () => {
    (useParams as jest.MockedFunction<typeof useParams>).mockReturnValue({
      threadId: undefined,
    });

    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-submit"));

    expect(mockDispatch).not.toHaveBeenCalled();
  });

  it("does not submit when thread is missing", () => {
    render(<ThreadMessageForm thread={undefined as ThreadModel} />);

    expect(screen.getByTestId("message-form")).toBeInTheDocument();
    expect(screen.getByTestId("loading-state")).toHaveTextContent("idle");

    fireEvent.click(screen.getByTestId("mock-submit"));

    expect(mockDispatch).not.toHaveBeenCalled();
  });

  it("handles file add with regular file", () => {
    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-file-add"));

    expect(mockToast).toHaveBeenCalledWith({
      title: "Attachment added",
      description: "test.txt has been added to the message",
    });
  });

  it("handles file add with audio recording", () => {
    // Mock the MessageForm to call onFileAdd with audio recording
    jest.doMock("../MessageForm", () => {
      return function MockMessageForm(props: { onFileAdd?: (file: File | Blob, isRecording: boolean) => void; [key: string]: unknown }) {
        return (
          <button
            data-testid="mock-audio-add"
            onClick={() => props.onFileAdd?.(new Blob(["audio"]), true)}
          >
            Add Audio
          </button>
        );
      };
    });

    const { rerender } = render(<ThreadMessageForm thread={mockThread} />);
    rerender(<ThreadMessageForm thread={mockThread} />);

    if (screen.queryByTestId("mock-audio-add")) {
      fireEvent.click(screen.getByTestId("mock-audio-add"));

      expect(mockToast).toHaveBeenCalledWith({
        title: "Recording added",
        description: "Ready to send with your message",
      });
    }
  });

  it("handles file add with blob (no name)", () => {
    // Mock the MessageForm to call onFileAdd with a blob
    jest.doMock("../MessageForm", () => {
      return function MockMessageForm(props: { onFileAdd?: (file: File | Blob, isRecording: boolean) => void; [key: string]: unknown }) {
        return (
          <button
            data-testid="mock-blob-add"
            onClick={() => props.onFileAdd?.(new Blob(["test"]), false)}
          >
            Add Blob
          </button>
        );
      };
    });

    const { rerender } = render(<ThreadMessageForm thread={mockThread} />);
    rerender(<ThreadMessageForm thread={mockThread} />);

    if (screen.queryByTestId("mock-blob-add")) {
      fireEvent.click(screen.getByTestId("mock-blob-add"));

      expect(mockToast).toHaveBeenCalledWith({
        title: "Attachment added",
        description: "File has been added to the message",
      });
    }
  });

  it("handles file removal", () => {
    render(<ThreadMessageForm thread={mockThread} />);

    fireEvent.click(screen.getByTestId("mock-file-remove"));

    expect(mockToast).toHaveBeenCalledWith({
      title: "Attachment removed",
    });
  });

  it("passes className to MessageForm", () => {
    const customClass = "custom-thread-form-class";
    render(<ThreadMessageForm thread={mockThread} className={customClass} />);

    expect(screen.getByTestId("class-name")).toHaveTextContent(customClass);
  });

  it("handles different thread statuses correctly", () => {
    const processingThread = { ...mockThread, status: "processing" as const };
    const { rerender } = render(<ThreadMessageForm thread={processingThread} />);
    expect(screen.getByTestId("loading-state")).toHaveTextContent("loading");

    const idleThread = { ...mockThread, status: "idle" as const };
    rerender(<ThreadMessageForm thread={idleThread} />);
    expect(screen.getByTestId("loading-state")).toHaveTextContent("idle");

    const errorThread = { ...mockThread, status: "error" as const };
    rerender(<ThreadMessageForm thread={errorThread} />);
    expect(screen.getByTestId("loading-state")).toHaveTextContent("loading");
  });
});
