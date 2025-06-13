import { vi } from 'vitest';
import { screen, render, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import ThreadUsersDialog from "../ThreadUsersDialog";
import * as threadActions from "../../actions/threadActions";
import { TooltipProvider } from "@/components/ui/tooltip";

// Mock Redux store
const createMockStore = (initialState: Record<string, unknown> = {}) => {
  return configureStore({
    reducer: () => initialState,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }),
  });
};

// Mock the threadActions module
vi.mock("../../actions/threadActions", () => ({
  fetchThreadUsers: vi.fn(),
  addUserByEmail: vi.fn(),
  removeThreadUser: vi.fn(),
  updateThreadUserRole: vi.fn(),
}));


// Mock the getThreadUsers and getUsers selectors
vi.mock("../../slices/threadsSlice", () => ({
  getThreadUsers: (state: Record<string, unknown>) => {
    return state.mockThreadUsers || [];
  }
}));

vi.mock("../../slices/usersSlice", () => ({
  getUsers: (state: Record<string, unknown>) => state.mockUsers || {}
}));

describe("ThreadUsersDialog", () => {
  const threadId = "thread-123";
  const mockThreadUsers = [
    {
      user_id: "user-1",
      role: "admin",
    },
    {
      user_id: "user-2",
      role: "user",
    },
  ];

  const mockUsers = {
    "user-1": {
      nickname: "User One",
      email: "user1@example.com",
      picture: "https://example.com/user1.jpg",
    },
    "user-2": {
      nickname: "User Two",
      email: "user2@example.com",
      picture: null,
    },
  };

  const mockState = {
    mockThreadUsers,
    mockUsers,
  };

  let store = createMockStore(mockState);

  beforeEach(() => {
    store = createMockStore(mockState);

    // Reset the mock implementations
    ((threadActions.fetchThreadUsers as unknown) as vi.Mock).mockImplementation(() => ({
      type: "fetchThreadUsers",
      payload: {
        threadId,
      },
      unwrap: vi.fn().mockResolvedValue({}),
    }));

    ((threadActions.addUserByEmail as unknown) as vi.Mock).mockImplementation(() => ({
      type: "addUserByEmail",
      payload: {
        threadId,
        email: "newuser@example.com",
      },
      unwrap: vi.fn().mockResolvedValue({}),
    }));

    ((threadActions.removeThreadUser as unknown) as vi.Mock).mockImplementation(() => ({
      type: "removeThreadUser",
      payload: {
        threadId,
        userId: "user-1",
      },
      unwrap: vi.fn().mockResolvedValue({}),
    }));

    ((threadActions.updateThreadUserRole as unknown) as vi.Mock).mockImplementation(() => ({
      type: "updateThreadUserRole",
      payload: {
        threadId,
        userId: "user-1",
        role: "user",
      },
      unwrap: vi.fn().mockResolvedValue({}),
    }));
  });

  const renderComponent = () => {
    return render(
      <Provider store={store}>
        <TooltipProvider>
          <ThreadUsersDialog threadId={threadId} />
        </TooltipProvider>
      </Provider>
    );
  };

  it("renders the component correctly", () => {
    renderComponent();
    // Test that the component renders without errors
    const usersIcon = document.querySelector(".lucide-users");
    expect(usersIcon).not.toBeNull();
  });

  it("calls fetchThreadUsers when dialog opens", async () => {
    renderComponent();

    // Find the button by SVG class
    const usersIcon = document.querySelector(".lucide-users");
    const button = usersIcon?.closest("button");

    // Click the button - this should open the dialog
    if (button) fireEvent.click(button);

    // Check that fetchThreadUsers was called
    await waitFor(() => {
      expect(threadActions.fetchThreadUsers).toHaveBeenCalledWith(threadId);
    });
  });

  it("allows adding a user by email", async () => {
    renderComponent();

    // Find and click the button to open the dialog
    const usersIcon = document.querySelector(".lucide-users");
    const button = usersIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Wait for dialog to open and form to be available
    await waitFor(async () => {
      // Find the input field and add button
      const emailInput = screen.getByPlaceholderText(/add user by email/i);
      expect(emailInput).toBeInTheDocument();

      // Fill in the email
      fireEvent.change(emailInput, { target: { value: "newuser@example.com" } });

      // Find the Add button and click it
      const addButton = screen.getAllByRole("button").find(button => button.textContent === "Add");
      if (addButton) {
        fireEvent.click(addButton);
      }
    });

    // Verify that the addUserByEmail action was called
    expect(threadActions.addUserByEmail).toHaveBeenCalledWith({
      threadId,
      email: "newuser@example.com",
    });
  });

  it("displays users correctly", async () => {
    renderComponent();

    // Find and click the button to open the dialog
    const usersIcon = document.querySelector(".lucide-users");
    const button = usersIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Wait for the user information to be displayed
    await waitFor(() => {
      expect(screen.getByText("User One")).toBeInTheDocument();
      expect(screen.getByText("User Two")).toBeInTheDocument();
      expect(screen.getByText("user1@example.com")).toBeInTheDocument();
      expect(screen.getByText("user2@example.com")).toBeInTheDocument();
    });
  });

  it("shows 'No users found' message when there are no users", async () => {
    // Create a store with an empty users list
    const emptyStore = createMockStore({
      mockThreadUsers: [],
      mockUsers: {},
    });

    render(
      <Provider store={emptyStore}>
        <TooltipProvider>
          <ThreadUsersDialog threadId={threadId} />
        </TooltipProvider>
      </Provider>
    );

    // Find and click the button to open the dialog
    const usersIcon = document.querySelector(".lucide-users");
    const button = usersIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Wait for the "No users found" message to be displayed
    await waitFor(() => {
      expect(screen.getByText(/no users found/i)).toBeInTheDocument();
    });
  });
});
