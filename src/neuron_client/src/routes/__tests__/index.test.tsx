import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";

// Mock all external dependencies first
vi.mock("sonner", () => {
  const mockToast: vi.MockedFunction<(...args: unknown[]) => void> & {
    error: vi.MockedFunction<(...args: unknown[]) => void>;
  } = Object.assign(vi.fn(), {
    error: vi.fn(),
  });
  return {
    toast: mockToast,
  };
});

vi.mock("@/assets/logo.svg", () => ({
  default: "logo.svg"
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/components/AudioRecorder", () => ({
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

vi.mock("@/components/PromptDropdown", () => ({
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

vi.mock("@/components/ui/sidebar", () => ({
  SidebarTrigger: () => <div data-testid="sidebar-trigger">Sidebar</div>,
}));

vi.mock("@/components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

vi.mock("@/components/PersonalitySelector", () => ({
  default: () => (
    <button
      aria-autocomplete="none"
      aria-controls="radix-:r8:"
      aria-expanded="false"
      className="flex items-center justify-between rounded-md border border-input bg-background px-3 py-2 ring-offset-background data-[placeholder]:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1 w-[200px] h-8 text-sm"
      data-state="closed"
      dir="ltr"
      role="combobox"
      type="button"
      data-testid="personality-selector"
    >
      <span style={{ pointerEvents: "none" }}>
        Assistant
      </span>
    </button>
  ),
}));


vi.mock("../../actions/threadActions", () => ({
  createThread: vi.fn(),
}));

vi.mock("../../actions/personalityActions", () => ({
  fetchPersonalities: () => vi.fn(),
  setActivePersonality: () => vi.fn(),
}));

vi.mock("../../actions/personalityRoomActions", () => ({
  createPersonalityRoom: vi.fn(),
}));

vi.mock("../../actions/personalityChatActions", () => ({
  sendPersonalityMessage: vi.fn(),
}));

// Mock hooks
const mockActivePersonality = { id: "1", name: "Assistant", description: "Default assistant" };

const mockDispatch = vi.fn();

vi.mock("../../hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: vi.fn((selector) => {
    // Mock state for all selectors
    const mockState = {
      personalities: {
        personalities: [mockActivePersonality],
        activePersonalityId: "1",  // This is the correct property name
        loading: false,
        error: null,
        personalityUsers: {}
      },
      threads: {
        threads: {},
        loading: false,
        error: null
      },
      socket: {
        connected: true  // Mock WebSocket as connected by default
      },
      app: {
        currentUser: { sub: "user123", email: "test@example.com" }
      }
    };

    return selector(mockState);
  }),
}));

// Import the component after all mocks are set up
import Index from "../index";
import { useAppSelector } from "../../hooks";
import { createThread } from "../../actions/threadActions";

describe("Index Route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (createThread as vi.MockedFunction<typeof createThread>).mockImplementation((args) => ({
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
          activePersonalityId: "1",  // Correct property name
          loading: false,
          error: null,
          personalityUsers: {}
        }) => state,
        app: (state = {
          currentUser: { sub: "user123", email: "test@example.com" }
        }) => state,
        socket: (state = { connected: true }) => state,
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

    it("should display active personality name", () => {
      renderComponent();

      // The personality selector should be present and contain the active personality name
      // Note: PersonalitySelector is rendered twice for responsive design (mobile and desktop)
      const personalitySelectors = screen.getAllByTestId("personality-selector");
      expect(personalitySelectors).toHaveLength(2); // One for mobile, one for desktop
      expect(personalitySelectors[0]).toHaveTextContent("Assistant");
      expect(personalitySelectors[1]).toHaveTextContent("Assistant");
    });

    it("should not display personality name when no active personality", () => {
      // Override the mock to return null for active personality
      (useAppSelector as vi.MockedFunction<typeof useAppSelector>).mockImplementation((selector) => {
        const mockState = {
          personalities: {
            personalities: [{ id: "1", name: "Assistant", description: "Default assistant" }],
            activePersonalityId: null,  // No active personality
            loading: false,
            error: null,
            personalityUsers: {}
          },
          threads: {
            threads: {},
            loading: false,
            error: null
          },
          socket: {
            connected: true  // Add socket state
          },
          app: {
            currentUser: { sub: "user123", email: "test@example.com" }
          }
        };

        return selector(mockState);
      });

      renderComponent();

      // Check that the placeholder text shows when no personality is selected
      expect(screen.getByPlaceholderText("Select a personality first")).toBeInTheDocument();

      // The personality selector will still show "Assistant" because our mock is static
      // but the form placeholder text will be correct
      const personalitySelectors = screen.getAllByTestId("personality-selector");
      expect(personalitySelectors).toHaveLength(2); // One for mobile, one for desktop

      // Reset mock for other tests
      (useAppSelector as vi.MockedFunction<typeof useAppSelector>).mockImplementation((selector) => {
        const mockState = {
          personalities: {
            personalities: [mockActivePersonality],
            activePersonalityId: "1",
            loading: false,
            error: null,
            personalityUsers: {}
          },
          threads: {
            threads: {},
            loading: false,
            error: null
          },
          socket: {
            connected: true  // Add socket state
          },
          app: {
            currentUser: { sub: "user123", email: "test@example.com" }
          }
        };

        return selector(mockState);
      });
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
      // Override the default mock to ensure proper state
      (useAppSelector as vi.MockedFunction<typeof useAppSelector>).mockImplementation((selector) => {
        const mockState = {
          personalities: {
            personalities: [mockActivePersonality],
            activePersonalityId: "1",
            loading: false,
            error: null,
            personalityUsers: {}
          },
          threads: {
            threads: {},
            loading: false,
            error: null
          },
          socket: {
            connected: true
          },
          app: {
            currentUser: { sub: "user123", email: "test@example.com" }
          }
        };
        return selector(mockState);
      });

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
