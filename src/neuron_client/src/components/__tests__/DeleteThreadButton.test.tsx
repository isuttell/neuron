import { screen, render, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import DeleteThreadButton from "../DeleteThreadButton";
import * as threadActions from "../../actions/threadActions";
import { TooltipProvider } from "@/components/ui/tooltip";

// Mock the Redux store
const createMockStore = () => {
  return configureStore({
    reducer: () => ({}),
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }),
  });
};

// Mock the navigate function
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

// Mock the threadActions module
jest.mock("../../actions/threadActions", () => ({
  deleteThread: jest.fn(),
}));

// Mock sonner toast
jest.mock("sonner", () => {
  const mockToast = jest.fn();
  mockToast.error = jest.fn();
  return {
    toast: mockToast,
  };
});

describe("DeleteThreadButton", () => {
  const threadId = "thread-123";
  let store = createMockStore();

  beforeEach(() => {
    store = createMockStore();

    // Reset the mock implementations
    ((threadActions.deleteThread as unknown) as jest.Mock).mockImplementation(() => ({
      type: "deleteThread",
      payload: threadId,
      unwrap: jest.fn().mockResolvedValue({}),
    }));

    mockNavigate.mockClear();
  });

  const renderComponent = () => {
    return render(
      <Provider store={store}>
        <MemoryRouter>
          <TooltipProvider>
            <DeleteThreadButton threadId={threadId} />
          </TooltipProvider>
        </MemoryRouter>
      </Provider>
    );
  };

  it("renders delete button with trash icon", () => {
    renderComponent();

    // Find the button with the trash icon
    const trashIcon = document.querySelector(".lucide-trash");
    expect(trashIcon).not.toBeNull();

    const button = trashIcon?.closest("button");
    expect(button).not.toBeNull();
  });

  it("opens confirmation dialog when clicked", async () => {
    renderComponent();

    // Find and click the delete button
    const trashIcon = document.querySelector(".lucide-trash");
    const button = trashIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Confirmation dialog should be open
    await waitFor(() => {
      expect(screen.getByText("Are you absolutely sure?")).toBeInTheDocument();
      expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();

      // Check for the action buttons
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /delete$/i })).toBeInTheDocument();
    });
  });

  it("navigates to home and deletes thread when delete is confirmed", async () => {
    renderComponent();

    // Find and click the delete button to open the dialog
    const trashIcon = document.querySelector(".lucide-trash");
    const button = trashIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Find and click the delete confirmation button
    await waitFor(() => {
      const deleteButton = screen.getByRole("button", { name: /delete$/i });
      fireEvent.click(deleteButton);
    });

    // Should navigate to home page
    expect(mockNavigate).toHaveBeenCalledWith("/");

    // Should call the deleteThread action with the correct threadId
    expect(threadActions.deleteThread).toHaveBeenCalledWith(threadId);
  });

  it("closes dialog without deleting when cancel is clicked", async () => {
    renderComponent();

    // Find and click the delete button to open the dialog
    const trashIcon = document.querySelector(".lucide-trash");
    const button = trashIcon?.closest("button");
    if (button) fireEvent.click(button);

    // Find and click the cancel button
    await waitFor(() => {
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);
    });

    // Navigate should not be called
    expect(mockNavigate).not.toHaveBeenCalled();

    // deleteThread action should not be called
    expect(threadActions.deleteThread).not.toHaveBeenCalled();
  });
});
