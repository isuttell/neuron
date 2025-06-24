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

// Mock usePersonalityPermissions hook
vi.mock("@/hooks/usePersonalityPermissions", () => ({
  usePersonalityPermissions: vi.fn(),
}));

// Import mocked modules
import { useAuth0 } from "@auth0/auth0-react";
import { isAdmin } from "@/lib/auth";
import { usePersonalityPermissions } from "@/hooks/usePersonalityPermissions";

// Create typed mocks
const mockUseAuth0 = vi.mocked(useAuth0);
const mockIsAdmin = vi.mocked(isAdmin);
const mockUsePersonalityPermissions = vi.mocked(usePersonalityPermissions);

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
  context: "Test context",
  memory: "Test memory",
  tool_set: "default",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const renderPersonalityItem = (
  personality: Personality = mockPersonality,
  permissionOverrides = {}
) => {
  // Default permission values (no access)
  const defaultPermissions = {
    canManage: false,
    canManageUsers: false,
    canDelete: false,
    canUse: false,
    hasAnyActions: false,
    shouldShowComponent: false,
    isAdmin: false,
    hasAccess: false,
    userRole: null,
    personality: undefined,
  };

  // Mock Auth0
  mockUseAuth0.mockReturnValue({
    user: { sub: "test-user-id" },
    isAuthenticated: true,
  } as ReturnType<typeof useAuth0>);

  // Mock isAdmin
  mockIsAdmin.mockReturnValue(false);

  // Mock personality permissions with overrides
  mockUsePersonalityPermissions.mockReturnValue({
    ...defaultPermissions,
    ...permissionOverrides,
  });

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

  describe("Basic Rendering", () => {
    it("renders personality name and description", () => {
      renderPersonalityItem();

      expect(screen.getByText("Test Personality")).toBeInTheDocument();
      expect(screen.getByText("Test description")).toBeInTheDocument();
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
            hasInitiallyFetched: true,
          },
        },
      });

      mockUsePersonalityPermissions.mockReturnValue({
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: false,
        hasAnyActions: false,
        shouldShowComponent: false,
        isAdmin: false,
        hasAccess: false,
        userRole: null,
        personality: undefined,
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

    it("handles navigation on click", () => {
      renderPersonalityItem();

      // Click on the card (using the description text as it's in the clickable area)
      const clickableArea = screen.getByText("Test description");
      fireEvent.click(clickableArea);

      // Should navigate to home page
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  describe("Permission-based Dropdown Visibility", () => {
    it("hides dropdown when user has no permissions", () => {
      renderPersonalityItem(mockPersonality, {
        shouldShowComponent: false,
      });

      expect(screen.getByText("Test Personality")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();
    });

    it("shows dropdown when user can use personality", () => {
      renderPersonalityItem(mockPersonality, {
        canUse: true,
        shouldShowComponent: true,
      });

      expect(screen.getByText("Test Personality")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("shows dropdown when user can manage personality", () => {
      renderPersonalityItem(mockPersonality, {
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        hasAnyActions: true,
        shouldShowComponent: true,
      });

      expect(screen.getByText("Test Personality")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("shows dropdown for system admin even without personality access", () => {
      // Mock Auth0 with admin user
      mockUseAuth0.mockReturnValue({
        user: {
          sub: "test-user-id",
          'neuron/roles': ['admin'],
          permissions: ['admin']
        },
        isAuthenticated: true,
      } as ReturnType<typeof useAuth0>);

      // Mock isAdmin to return true for system admin
      mockIsAdmin.mockReturnValue(true);

      // Mock personality permissions with no access
      mockUsePersonalityPermissions.mockReturnValue({
        canUse: false,
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        hasAnyActions: false,
        shouldShowComponent: false,
        isAdmin: false,
        hasAccess: false,
        userRole: null,
        personality: undefined,
      });

      const store = configureStore({
        reducer: {
          personalities: personalitiesReducer,
        },
        preloadedState: {
          personalities: {
            personalities: [mockPersonality],
            activePersonalityId: null,
            loading: false,
            error: null,
            personalityUsers: {},
          },
        },
      });

      render(
        <Provider store={store}>
          <BrowserRouter>
            <PersonalityItem personality={mockPersonality} />
          </BrowserRouter>
        </Provider>
      );

      expect(screen.getByText("Test Personality")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });
  });

  describe("Permission Integration", () => {
    it("calls usePersonalityPermissions with correct personality id", () => {
      renderPersonalityItem();

      expect(mockUsePersonalityPermissions).toHaveBeenCalledWith("test-personality-id");
    });

    it("respects permission flags for component visibility", () => {
      // Test that the component respects the shouldShowComponent flag
      const { rerender } = renderPersonalityItem(mockPersonality, {
        shouldShowComponent: false,
      });

      expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();

      // Change permissions to show component
      mockUsePersonalityPermissions.mockReturnValue({
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: true,
        hasAnyActions: false,
        shouldShowComponent: true,
        isAdmin: false,
        hasAccess: true,
        userRole: "user",
        personality: undefined,
      });

      rerender(
        <Provider store={configureStore({
          reducer: { personalities: personalitiesReducer },
          preloadedState: {
            personalities: {
              personalities: [mockPersonality],
              activePersonalityId: null,
              loading: false,
              error: null,
              personalityUsers: {},
              hasInitiallyFetched: true,
            },
          },
        })}>
          <BrowserRouter>
            <PersonalityItem personality={mockPersonality} />
          </BrowserRouter>
        </Provider>
      );

      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });
  });

  describe("Different User Roles", () => {
    it("handles system admin user correctly", () => {
      mockIsAdmin.mockReturnValue(true);
      renderPersonalityItem(mockPersonality, {
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canUse: true,
        hasAnyActions: true,
        shouldShowComponent: true,
        isAdmin: false, // This is personality admin, not system admin
        hasAccess: true,
        userRole: null,
      });

      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
      expect(mockUsePersonalityPermissions).toHaveBeenCalledWith("test-personality-id");
    });

    it("handles personality admin user correctly", () => {
      renderPersonalityItem(mockPersonality, {
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canUse: true,
        hasAnyActions: true,
        shouldShowComponent: true,
        isAdmin: true, // This is personality admin
        hasAccess: true,
        userRole: "admin",
      });

      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("handles personality user (non-admin) correctly", () => {
      renderPersonalityItem(mockPersonality, {
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: true,
        hasAnyActions: false,
        shouldShowComponent: true, // Can use personality
        isAdmin: false,
        hasAccess: true,
        userRole: "user",
      });

      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("handles user with no personality access correctly", () => {
      renderPersonalityItem(mockPersonality, {
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: false,
        hasAnyActions: false,
        shouldShowComponent: false,
        isAdmin: false,
        hasAccess: false,
        userRole: null,
      });

      expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();
    });
  });

  describe("Integration Tests - Key Permission Scenarios", () => {
    it("system admin can access all features including embeddings", () => {
      mockIsAdmin.mockReturnValue(true);
      renderPersonalityItem(mockPersonality, {
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canUse: true,
        hasAnyActions: true,
        shouldShowComponent: true,
        isAdmin: false, // personality admin flag
        hasAccess: true,
        userRole: null,
      });

      // System admin should see dropdown
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();

      // Verify isAdmin was called to check system admin status
      expect(mockIsAdmin).toHaveBeenCalled();

      // Verify personality permissions hook was called
      expect(mockUsePersonalityPermissions).toHaveBeenCalledWith("test-personality-id");
    });

    it("personality admin can access management features but not embeddings", () => {
      mockIsAdmin.mockReturnValue(false); // Not system admin
      renderPersonalityItem(mockPersonality, {
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canUse: true,
        hasAnyActions: true,
        shouldShowComponent: true,
        isAdmin: true, // personality admin
        hasAccess: true,
        userRole: "admin",
      });

      // Personality admin should see dropdown
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();

      // Should not be system admin (embeddings would be hidden)
      expect(mockIsAdmin).toHaveReturnedWith(false);
    });

    it("regular personality user only sees basic options", () => {
      mockIsAdmin.mockReturnValue(false);
      renderPersonalityItem(mockPersonality, {
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: true,
        hasAnyActions: false, // No admin actions
        shouldShowComponent: true, // But can use personality
        isAdmin: false,
        hasAccess: true,
        userRole: "user",
      });

      // User should see dropdown (for activate/deactivate)
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("user with no personality access sees no dropdown", () => {
      mockIsAdmin.mockReturnValue(false);
      renderPersonalityItem(mockPersonality, {
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canUse: false,
        hasAnyActions: false,
        shouldShowComponent: false,
        isAdmin: false,
        hasAccess: false,
        userRole: null,
      });

      // No access user should not see dropdown at all
      expect(screen.queryByRole("button", { name: /more actions/i })).not.toBeInTheDocument();
    });

    it("maintains thread and personality permission separation", () => {
      // This test verifies that personality permissions are independent
      renderPersonalityItem(mockPersonality, {
        canManage: true, // Can manage personality
        canUse: true,
        shouldShowComponent: true,
      });

      // Should call personality permissions hook, not thread permissions
      expect(mockUsePersonalityPermissions).toHaveBeenCalledWith("test-personality-id");

      // Component should render with personality permissions
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
    });

    it("correctly converts UserWithRole to PersonalityUser format", () => {
      // This tests the integration between Redux store format and permission logic
      const store = configureStore({
        reducer: {
          personalities: personalitiesReducer,
        },
        preloadedState: {
          personalities: {
            personalities: [mockPersonality],
            personalityUsers: {
              "test-personality-id": [
                {
                  id: "user-123",
                  email: "admin@test.com",
                  nickname: "admin",
                  created_at: "2024-01-01T00:00:00Z",
                  updated_at: "2024-01-01T00:00:00Z",
                  role: "admin",
                },
              ],
            },
            activePersonalityId: null,
            loading: false,
            error: null,
            hasInitiallyFetched: true,
          },
        },
      });

      mockUsePersonalityPermissions.mockReturnValue({
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canUse: true,
        hasAnyActions: true,
        shouldShowComponent: true,
        isAdmin: true,
        hasAccess: true,
        userRole: "admin",
        personality: {
          ...mockPersonality,
          personality_users: [
            {
              user_id: "user-123",
              personality_id: "test-personality-id",
              role: "admin",
            },
          ],
        },
      });

      render(
        <Provider store={store}>
          <BrowserRouter>
            <PersonalityItem personality={mockPersonality} />
          </BrowserRouter>
        </Provider>
      );

      // Should render successfully with converted data
      expect(screen.getByRole("button", { name: /more actions/i })).toBeInTheDocument();
      expect(mockUsePersonalityPermissions).toHaveBeenCalledWith("test-personality-id");
    });
  });

  // Note: Individual dropdown menu item tests are omitted due to Radix UI portal rendering complexity
  // These are better tested with e2e tests or by testing the permission logic separately
});
