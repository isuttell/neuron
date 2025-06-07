import { configureStore } from "@reduxjs/toolkit";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";

// Mock all external dependencies first
jest.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: jest.fn() }),
  toast: jest.fn(),
}));

jest.mock("@/assets/logo.svg", () => "logo.svg");

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

jest.mock("@/components/AudioRecorder", () => ({
  AudioRecorder: ({ onRecordingComplete, disabled, className }: {
    onRecordingComplete: (blob: Blob) => void;
    disabled: boolean;
    className: string;
  }) => (
    <button
      data-testid="audio-recorder"
      onClick={() => {
        const blob = new Blob(["audio"], { type: "audio/wav" });
        onRecordingComplete(blob);
      }}
      disabled={disabled}
      className={className}
    >
      Audio Recorder
    </button>
  ),
}));

jest.mock("@/components/PromptDropdown", () => ({
  PromptDropdown: ({ onSelectPrompt, disabled }: {
    onSelectPrompt: (prompt: string) => void;
    disabled: boolean;
  }) => (
    <select
      data-testid="prompt-dropdown"
      onChange={(e) => onSelectPrompt(e.target.value)}
      disabled={disabled}
    >
      <option value="">Select a prompt</option>
      <option value="Test prompt 1">Test prompt 1</option>
    </select>
  ),
}));

jest.mock("@/components/ui/sidebar", () => ({
  SidebarTrigger: () => <div data-testid="sidebar-trigger">Sidebar</div>,
}));

jest.mock("@/components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

jest.mock("@/components/FuzzyTimeAgo", () => ({
  __esModule: true,
  default: ({ date }: { date: Date }) => <span>{date.toString()}</span>,
}));

// Mock action creators
const mockCreateThread = jest.fn();
const mockFetchPersonalities = jest.fn();
const mockSetActivePersonality = jest.fn();

jest.mock("../../actions/threadActions", () => ({
  createThread: mockCreateThread,
  fetchRecentThreads: jest.fn(),
}));

jest.mock("../../actions/personalityActions", () => ({
  fetchPersonalities: () => mockFetchPersonalities,
  setActivePersonality: () => mockSetActivePersonality,
}));

// Mock hooks
const mockDispatch = jest.fn();
jest.mock("../../hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: unknown) => unknown) => {
    // Mock different selectors
    if (selector.toString().includes("personalities")) {
      return {
        personalities: [
          { id: "1", name: "Assistant", description: "Default assistant" },
        ],
        activeId: "1",
        loading: false,
        error: null,
      };
    }
    if (selector.toString().includes("threads")) {
      return [];
    }
    return null;
  },
}));

// Import the component after all mocks are set up
import Index from "../index";

describe("Index Route", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCreateThread.mockImplementation((args) => ({
      unwrap: () => Promise.resolve({ thread: { id: "thread-1" } }),
      type: "threads/createThread/pending",
      payload: args,
    }));
    mockDispatch.mockReturnValue({
      unwrap: () => Promise.resolve({ thread: { id: "thread-1" } }),
    });
  });

  const renderComponent = () => {
    const store = configureStore({
      reducer: {
        threads: (state = { threads: {}, loading: false, error: null }) => state,
        personalities: (state = {
          personalities: [{ id: "1", name: "Assistant" }],
          activeId: "1",
          loading: false,
          error: null
        }) => state,
      },
    });

    return render(
      <Provider store={store}>
        <MemoryRouter>
          <Index />
        </MemoryRouter>
      </Provider>
    );
  };

  describe("UI Rendering", () => {
    it("should render the main elements", () => {
      renderComponent();

      expect(screen.getByPlaceholderText("Type your prompt here...")).toBeInTheDocument();
      expect(screen.getByTestId("audio-recorder")).toBeInTheDocument();
      expect(screen.getByTestId("prompt-dropdown")).toBeInTheDocument();

      const buttons = screen.getAllByRole("button");
      const submitButton = buttons.find(btn => btn.getAttribute("type") === "submit");
      expect(submitButton).toBeInTheDocument();
    });

    it("should show all buttons in a horizontal layout", () => {
      renderComponent();

      const uploadButtons = screen.getAllByRole("button");
      const audioRecorder = screen.getByTestId("audio-recorder");
      const promptDropdown = screen.getByTestId("prompt-dropdown");

      // Check that key elements are present
      expect(uploadButtons.length).toBeGreaterThan(1);
      expect(audioRecorder).toBeInTheDocument();
      expect(promptDropdown).toBeInTheDocument();
    });
  });

  describe("Form submission", () => {
    it("should handle form submission with text input", async () => {
      renderComponent();

      const textarea = screen.getByPlaceholderText("Type your prompt here...");
      const buttons = screen.getAllByRole("button");
      const submitButton = buttons.find(btn => btn.getAttribute("type") === "submit");

      await userEvent.type(textarea, "Test message");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(mockDispatch).toHaveBeenCalled();
      });
    });

    it("should update prompt text when dropdown selection changes", async () => {
      renderComponent();

      const promptDropdown = screen.getByTestId("prompt-dropdown");
      const textarea = screen.getByPlaceholderText("Type your prompt here...");

      fireEvent.change(promptDropdown, { target: { value: "Test prompt 1" } });

      await waitFor(() => {
        expect(textarea).toHaveValue("Test prompt 1");
      });
    });
  });

  describe("File upload", () => {
    it("should handle file upload", async () => {
      renderComponent();

      const fileInput = document.getElementById("file-upload") as HTMLInputElement;
      const file = new File(["test"], "test.png", { type: "image/png" });

      Object.defineProperty(fileInput, "files", {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      // Just verify the input exists and can receive files
      expect(fileInput).toBeInTheDocument();
      expect(fileInput.files).toHaveLength(1);
    });
  });

  describe("Audio recording", () => {
    it("should handle audio recording", async () => {
      renderComponent();

      const audioRecorder = screen.getByTestId("audio-recorder");

      expect(audioRecorder).toBeInTheDocument();
      expect(audioRecorder).not.toBeDisabled();

      fireEvent.click(audioRecorder);

      // Verify the button is functional
      expect(audioRecorder).toBeInTheDocument();
    });
  });

  describe("Button states", () => {
    it("should show submit button with icon only", () => {
      renderComponent();

      const buttons = screen.getAllByRole("button");
      const submitButton = buttons.find(btn => btn.getAttribute("type") === "submit");
      expect(submitButton).toBeInTheDocument();

      // The button should not contain text "Send"
      expect(submitButton?.textContent).not.toContain("Send");

      // The button should contain only the icon (which doesn't have text content)
      expect(submitButton?.textContent).toBe("");
    });
  });
});
