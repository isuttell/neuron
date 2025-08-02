import { vi } from 'vitest';
import { screen, render, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import DeletePersonalityDialog from "../DeletePersonalityDialog";
import * as personalityActions from "../../actions/personalityActions";
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

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the personalityActions module
vi.mock("../../actions/personalityActions", () => ({
  deletePersonality: vi.fn(),
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

describe("DeletePersonalityDialog", () => {
  const personalityId = "personality-123";
  let store = createMockStore();

  beforeEach(() => {
    store = createMockStore();

    // Reset the mock implementations
    ((personalityActions.deletePersonality as unknown) as vi.Mock).mockImplementation(() => ({
      type: "deletePersonality",
      payload: personalityId,
      unwrap: vi.fn().mockResolvedValue({}),
    }));

    mockNavigate.mockClear();
  });

  const renderComponent = (props: any = {}) => {
    return render(
      <Provider store={store}>
        <MemoryRouter>
          <TooltipProvider>
            <DeletePersonalityDialog
              personalityId={personalityId}
              personalityName="Test Personality"
              open={true}
              trigger={<></>}
              {...props}
            />
          </TooltipProvider>
        </MemoryRouter>
      </Provider>
    );
  };

  it("renders dialog when open", () => {
    renderComponent();

    expect(screen.getByText("Are you absolutely sure?")).toBeInTheDocument();
    expect(screen.getByText(/This will permanently delete the personality "Test Personality"/)).toBeInTheDocument();
  });

  it("navigates to home and deletes personality when delete is confirmed", async () => {
    renderComponent();

    // Find and click the delete confirmation button
    const deleteButton = screen.getByRole("button", { name: /delete$/i });
    fireEvent.click(deleteButton);

    // Should navigate to home page
    expect(mockNavigate).toHaveBeenCalledWith("/");

    // Should call the deletePersonality action with the correct personalityId
    expect(personalityActions.deletePersonality).toHaveBeenCalledWith(personalityId);
  });

  it("renders without personality name", () => {
    renderComponent({ personalityName: undefined });

    expect(screen.getByText("Are you absolutely sure?")).toBeInTheDocument();
    expect(screen.getByText(/This will permanently delete the personality\./)).toBeInTheDocument();
  });

  it("renders default trigger when no trigger is provided", () => {
    render(
      <Provider store={store}>
        <MemoryRouter>
          <TooltipProvider>
            <DeletePersonalityDialog personalityId={personalityId} />
          </TooltipProvider>
        </MemoryRouter>
      </Provider>
    );

    // Check for the trash icon in the default trigger
    const trashIcon = document.querySelector(".lucide-trash");
    expect(trashIcon).not.toBeNull();

    const button = trashIcon?.closest("button");
    expect(button).not.toBeNull();
  });
});
