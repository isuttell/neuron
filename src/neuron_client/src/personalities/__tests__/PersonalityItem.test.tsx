import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import PersonalityItem from "../PersonalityItem";
import { Personality } from "@/slices/personalitiesSlice.d";
import personalitiesReducer from "@/slices/personalitiesSlice";

// Mock Auth0
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

// Mock isAdmin function
vi.mock("@/lib/auth", () => ({
  isAdmin: vi.fn(),
}));

// Import mocked modules
import { useAuth0 } from "@auth0/auth0-react";
import { isAdmin } from "@/lib/auth";

// Mock the dialogs
vi.mock("@/personalities/EditPersonalityDialog", () => ({
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="edit-personality-dialog">Edit Personality Dialog</div> : null,
}));

vi.mock("@/personalities/PersonalityUsersDialog", () => ({
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="personality-users-dialog">Personality Users Dialog</div> : null,
}));

// Mock toast
vi.mock("sonner", () => ({
  toast: Object.assign(vi.fn(), {
    error: vi.fn(),
  }),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockPersonality: Personality = {
  id: "test-personality-id",
  name: "Test Personality",
  description: "Test description",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  is_active: false,
  user_id: "test-user-id",
  role: "user",
  visibility: "private",
};

const renderPersonalityItem = (
  personality: Personality = mockPersonality,
  userIsAdmin = false
) => {
  // Mock Auth0 and isAdmin based on test needs
  vi.mocked(useAuth0).mockReturnValue({
    user: { sub: "test-user-id" },
    isAuthenticated: true,
  } as ReturnType<typeof useAuth0>);
  vi.mocked(isAdmin).mockReturnValue(userIsAdmin);

  const store = configureStore({
    reducer: {
      personalities: personalitiesReducer,
    },
    preloadedState: {
      personalities: {
        personalities: [personality],
        activePersonalityId: null,
        loading: false,
        error: null,
        personalityUsers: {},
      },
    },
  });

  return render(
    <Provider store={store}>
      <BrowserRouter>
        <PersonalityItem personality={personality} />
      </BrowserRouter>
    </Provider>
  );
};

describe("PersonalityItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders personality without dropdown for non-admin users", () => {
    renderPersonalityItem();

    expect(screen.getByText("Test Personality")).toBeInTheDocument();
    expect(screen.getByText("Test description")).toBeInTheDocument();

    // Dropdown button should not be visible for non-admin
    expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();
  });

  it("renders personality with dropdown for admin users", () => {
    renderPersonalityItem(mockPersonality, true);

    expect(screen.getByText("Test Personality")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
  });

  it("shows active indicator for active personality", () => {
    const activePersonality = { ...mockPersonality };
    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
      preloadedState: {
        personalities: {
          personalities: [activePersonality],
          activePersonalityId: activePersonality.id,
          loading: false,
          error: null,
          personalityUsers: {},
        },
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <PersonalityItem personality={activePersonality} />
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders personality with logo when available", () => {
    const personalityWithLogo = {
      ...mockPersonality,
      logo: "https://example.com/logo.png",
    };

    renderPersonalityItem(personalityWithLogo);

    const logo = screen.getByAltText("Test Personality logo");
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute("src", "https://example.com/logo_t.webp");
  });

  it("handles navigation on click for non-admin users", () => {
    renderPersonalityItem();

    // Click on the card (using the description text as it's in the clickable area)
    const clickableArea = screen.getByText("Test description");
    fireEvent.click(clickableArea);

    // Should navigate to home page
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("does not show dropdown for non-admin users with active personality", () => {
    const activePersonality = { ...mockPersonality };
    vi.mocked(useAuth0).mockReturnValue({
      user: { sub: "test-user-id" },
      isAuthenticated: true,
    } as ReturnType<typeof useAuth0>);
    vi.mocked(isAdmin).mockReturnValue(false);

    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
      preloadedState: {
        personalities: {
          personalities: [activePersonality],
          activePersonalityId: activePersonality.id,
          loading: false,
          error: null,
          personalityUsers: {},
        },
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <PersonalityItem personality={activePersonality} />
        </BrowserRouter>
      </Provider>
    );

    // Should show active indicator but no dropdown
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();
  });

  // Note: Dropdown menu interaction tests are omitted due to Radix UI portal rendering complexity in test environment
  // These interactions are better tested with e2e tests or by mocking the dropdown menu component
});
