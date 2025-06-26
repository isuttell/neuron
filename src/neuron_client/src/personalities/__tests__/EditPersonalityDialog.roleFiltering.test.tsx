import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useAuth0 } from "@auth0/auth0-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import EditPersonalityDialog from "../EditPersonalityDialog";
import { appSlice } from "../../slices/appSlice";
import { personalitiesSlice } from "../../slices/personalitiesSlice";

// Mock Auth0
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const createMockStore = (protectedToolSets: Record<string, string> | undefined = undefined) => {
  return configureStore({
    reducer: {
      app: appSlice.reducer,
      personalities: personalitiesSlice.reducer,
    },
    preloadedState: {
      app: {
        sidebar_image: "",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets,
        isLoading: false,
        error: null,
        currentUser: null,
      },
      personalities: {
        personalities: [],
        personalityUsers: {},
        activePersonalityId: undefined,
        loading: false,
        error: null,
        hasInitiallyFetched: true,
      },
    },
  });
};

const mockUser = (roles: string[]) => {
  (useAuth0 as jest.MockedFunction<typeof useAuth0>).mockReturnValue({
    user: {
      "neuron/roles": roles,
    },
    isAuthenticated: true,
    isLoading: false,
  });
};

const renderWithProviders = (component: React.ReactElement, store: ReturnType<typeof configureStore>) => {
  return render(
    <Provider store={store}>
      <TooltipProvider>
        {component}
      </TooltipProvider>
    </Provider>
  );
};

describe("EditPersonalityDialog Role-Based Filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("tool set filtering based on user roles", () => {
    it("should show all tool sets when user has all required roles", async () => {
      mockUser(["tool-homeassistant", "tool-kepler", "admin"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // All tool sets should be available
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.getByText("Kepler")).toBeInTheDocument();
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should hide protected tool sets when user lacks required roles", async () => {
      mockUser(["regular-user"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // Protected tool sets should be hidden
        expect(screen.queryByText("Smart Home")).not.toBeInTheDocument();
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument();

        // Non-protected tool sets should be visible
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should show only tool sets user has roles for", async () => {
      mockUser(["tool-homeassistant"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // User has homeassistant role
        expect(screen.getByText("Smart Home")).toBeInTheDocument();

        // User lacks kepler role
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument();

        // Non-protected tool sets should be visible
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should show all tool sets when protectedToolSets config is empty", async () => {
      mockUser(["regular-user"]);

      const store = createMockStore({});

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // All tool sets should be available since none are protected
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.getByText("Kepler")).toBeInTheDocument();
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should show all tool sets when protectedToolSets config is undefined", async () => {
      mockUser(["regular-user"]);

      const store = createMockStore(undefined);

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // All tool sets should be available since config is not loaded
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.getByText("Kepler")).toBeInTheDocument();
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });
  });

  describe("user role edge cases", () => {
    it("should handle user with no roles", async () => {
      mockUser([]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // Protected tool sets should be hidden
        expect(screen.queryByText("Smart Home")).not.toBeInTheDocument();
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument();

        // Non-protected tool sets should be visible
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should handle undefined user", async () => {
      (useAuth0 as jest.MockedFunction<typeof useAuth0>).mockReturnValue({
        user: undefined,
        isAuthenticated: false,
        isLoading: false,
      });

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // Protected tool sets should be hidden when no user
        expect(screen.queryByText("Smart Home")).not.toBeInTheDocument();
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument();

        // Non-protected tool sets should be visible
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });

    it("should handle user with extra roles", async () => {
      mockUser([
        "tool-homeassistant",
        "tool-kepler",
        "admin",
        "super-user",
        "tool-nonexistent",
      ]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        // Should have access to all tool sets including protected ones
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.getByText("Kepler")).toBeInTheDocument();
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
        expect(screen.getByText("Search")).toBeInTheDocument();
      });
    });
  });

  describe("dynamic configuration changes", () => {
    it("should update available tool sets when protectedToolSets config changes", async () => {
      mockUser(["tool-homeassistant"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
      });

      const { rerender } = renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.getByText("Kepler")).toBeInTheDocument(); // Not protected yet
      });

      // Update the store to add kepler as protected
      store.dispatch({
        type: "app/fetchConfig/fulfilled",
        payload: {
          sidebar_image: "",
          api: { baseUrl: "/api", wsEndpoint: "/ws" },
          protectedToolSets: {
            homeassistant: "tool-homeassistant",
            kepler: "tool-kepler",
          },
        },
      });

      rerender(
        <Provider store={store}>
          <TooltipProvider>
            <EditPersonalityDialog open={true} onOpenChange={() => {}} />
          </TooltipProvider>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText("Smart Home")).toBeInTheDocument();
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument(); // Now protected
      });
    });
  });

  describe("tool set selection behavior", () => {
    it("should allow selection of available tool sets only", async () => {
      mockUser(["tool-homeassistant"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        expect(screen.getByRole("group")).toBeInTheDocument();

        // Should be able to find homeassistant toggle
        const homeassistantToggle = screen.getByText("Smart Home");
        expect(homeassistantToggle).toBeInTheDocument();

        // Should not find kepler toggle
        expect(screen.queryByText("Kepler")).not.toBeInTheDocument();

        // Should find non-protected toggles
        expect(screen.getByText("Image Generation")).toBeInTheDocument();
      });
    });
  });

  describe("accessibility and usability", () => {
    it("should maintain proper accessibility when tool sets are filtered", async () => {
      mockUser(["tool-homeassistant"]);

      const store = createMockStore({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });

      renderWithProviders(
        <EditPersonalityDialog open={true} onOpenChange={() => {}} />,
        store
      );

      await waitFor(() => {
        expect(screen.getByRole("group")).toBeInTheDocument();

        // Ensure proper ARIA attributes are maintained
        const availableToggles = screen.getAllByRole("button");
        expect(availableToggles.length).toBeGreaterThan(0);

        // Each visible toggle should be properly accessible
        availableToggles.forEach((toggle) => {
          expect(toggle).toBeVisible();
          expect(toggle).not.toBeDisabled();
        });
      });
    });
  });
});
