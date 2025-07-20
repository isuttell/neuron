import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import "@testing-library/jest-dom";
import { render, screen, act } from "@testing-library/react";
import React from "react";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import * as hooks from "../../hooks";
import { RootComponent } from "../root";

import * as auth0React from "@auth0/auth0-react";
import { Auth0ContextInterface, User } from "@auth0/auth0-react";
import * as apiModule from "../../lib/api";

// Mock Auth0 hook
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
  withAuthenticationRequired: vi.fn((component) => component),
}));

// Mock API client
vi.mock("../../lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

// Mock all the imported components
vi.mock("@/components/layout/MainSidebar", () => ({
  MainSidebar: () => <div data-testid="main-sidebar">MainSidebar</div>,
}));

vi.mock("@/components/ThreadTitleUpdater", () => ({
  ThreadTitleUpdater: () => <div>ThreadTitleUpdater</div>,
}));

vi.mock("@/components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

vi.mock("@/components/ui/sidebar", () => ({
  SidebarProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock dispatch and selector hooks
const mockDispatch = vi.fn();
const useAppDispatchMock = vi.spyOn(hooks, "useAppDispatch");
const useAppSelectorMock = vi.spyOn(hooks, "useAppSelector");

describe("RootComponent", () => {
  // Reset mocks before each test
  beforeEach(() => {
    vi.clearAllMocks();
    useAppDispatchMock.mockReturnValue(mockDispatch);
  });

  const mockGetAccessTokenSilently = vi.fn().mockResolvedValue("mock-token");

  // Setup auth0 mock with different states
  const setupAuth0Mock = (options: {
    isAuthenticated: boolean;
    isLoading: boolean;
    error?: Error | undefined;
  }) => {
    const { isAuthenticated, isLoading, error } = options;

    const useAuth0Mock = vi.spyOn(auth0React, "useAuth0");
    useAuth0Mock.mockReturnValue({
      isAuthenticated,
      isLoading,
      error,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenWithPopup: vi.fn(),
      getIdTokenClaims: vi.fn(),
      loginWithPopup: vi.fn(),
      handleRedirectCallback: vi.fn(),
      user: {
        nickname: "testuser",
        picture: "https://example.com/avatar.png",
        "neuron/roles": ["admin"] // Admin role needed for provider access
      } as User,
    } as Auth0ContextInterface<User>);
  };

  // Helper function to setup mock API responses
  const setupApiMock = (success: boolean = true) => {
    const apiMock = apiModule.api;
    if (success) {
      (apiMock.post as vi.Mock).mockResolvedValue({ status: "success" });
    } else {
      (apiMock.post as vi.Mock).mockRejectedValue(new Error("API error"));
    }
  };

  const renderComponent = (connectionStatus = true) => {
    // Mock connection status
    useAppSelectorMock.mockReturnValue(connectionStatus);

    const store = configureStore({
      reducer: {
        app: (state = {}) => state,
        socket: (state = { connected: connectionStatus }) => state,
      },
    });

    // Use Routes with a specific path to avoid pathname issues
    return render(
      <Provider store={store}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<RootComponent />} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
  };

  it("shows loading spinner when still loading auth", async () => {
    setupAuth0Mock({ isAuthenticated: false, isLoading: true });

    await act(async () => {
      renderComponent();
    });

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("main-sidebar")).not.toBeInTheDocument();
  });

  it("redirects to login when not authenticated", async () => {
    const loginWithRedirect = vi.fn();

    setupAuth0Mock({ isAuthenticated: false, isLoading: false });
    vi.spyOn(auth0React, "useAuth0").mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: undefined,
      loginWithRedirect,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      logout: vi.fn(),
      getAccessTokenWithPopup: vi.fn(),
      getIdTokenClaims: vi.fn(),
      loginWithPopup: vi.fn(),
      handleRedirectCallback: vi.fn(),
      user: undefined,
    } as Auth0ContextInterface<User>);

    await act(async () => {
      renderComponent();
    });

    expect(loginWithRedirect).toHaveBeenCalled();
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  it("shows error page when auth error occurs", async () => {
    setupAuth0Mock({
      isAuthenticated: false,
      isLoading: false,
      error: new Error("Auth error"),
    });

    await act(async () => {
      renderComponent();
    });

    expect(screen.getByText("Oops!")).toBeInTheDocument();
    expect(screen.getByText("Error: Auth error")).toBeInTheDocument();
  });

  it("renders content even when not connected (WebSocket disconnection should not unmount app)", async () => {
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    setupApiMock(true);

    // Mock state to simulate the userSynced state being true
    const useStateMock = vi.spyOn(React, 'useState');
    useStateMock.mockImplementationOnce(() => {
      return [true, vi.fn()]; // Simulate userSynced=true
    });

    // Connection status is false, but app should still render
    await act(async () => {
      renderComponent(false);
    });

    // Should render content even when disconnected (no more unmounting on WebSocket disconnect)
    expect(screen.getByTestId("main-sidebar")).toBeInTheDocument();
  });

  it("shows spinner when not fully synced with backend", async () => {
    // Create necessary mocks
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    const apiMock = apiModule.api;

    // Don't resolve the promise - keep it pending so userSynced stays false
    (apiMock.post as vi.Mock).mockImplementation(() => new Promise(() => {}));

    // Render the component using act to handle async state updates
    await act(async () => {
      renderComponent(true);
    });

    // Should still be loading because userSynced is false
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("main-sidebar")).not.toBeInTheDocument();

    // Verify API call was attempted
    expect(apiMock.post).toHaveBeenCalledWith("/users/login", {});
  });

  // Verify that content only renders when all required conditions are met
  it("renders content only when authenticated and user is synced (connection no longer required)", async () => {
    // Mock auth and API
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    const apiMock = apiModule.api;
    (apiMock.post as vi.Mock).mockResolvedValue({ status: "success" });

    // Mock state to simulate the userSynced state being true
    const useStateMock = vi.spyOn(React, 'useState');
    useStateMock.mockImplementationOnce(() => {
      return [true, vi.fn()]; // Simulate userSynced=true
    });

    // Mock connected status
    useAppSelectorMock.mockReturnValue(true); // isConnected = true

    // Create fresh render container to avoid conflicts
    const container = document.createElement('div');
    document.body.appendChild(container);

    // Render with all conditions met using act to handle state updates
    await act(async () => {
      render(
        <Provider store={configureStore({
          reducer: {
            app: (state = {}) => state,
            socket: (state = { connected: true }) => state,
          },
        })}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<RootComponent />} />
            </Routes>
          </MemoryRouter>
        </Provider>,
        { container }
      );
    });

    // Verify API call was made
    expect(apiMock.post).toHaveBeenCalledWith("/users/login", {});

    // Since we're mocking userSynced=true, content should be visible
    expect(container.querySelector('[data-testid="main-sidebar"]')).toBeInTheDocument();

    // Clean up
    document.body.removeChild(container);
  });

  it("connects socket and fetches initial data upon authentication", async () => {
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    setupApiMock(true);

    // Use act to handle async state updates
    await act(async () => {
      renderComponent(true);
    });

    expect(mockDispatch).toHaveBeenCalledWith({ type: "socket/connect" });
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchConfig
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchMediaLists
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchProviders
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchPersonalities
  });

  it("does not fetch providers when user is not admin", async () => {
    // Setup non-admin user
    const useAuth0Mock = vi.spyOn(auth0React, "useAuth0");
    useAuth0Mock.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: undefined,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenWithPopup: vi.fn(),
      getIdTokenClaims: vi.fn(),
      loginWithPopup: vi.fn(),
      handleRedirectCallback: vi.fn(),
      user: {
        nickname: "testuser",
        picture: "https://example.com/avatar.png",
        "neuron/roles": [] // No admin role
      } as User,
    } as Auth0ContextInterface<User>);

    setupApiMock(true);

    // Use act to handle async state updates
    await act(async () => {
      renderComponent(true);
    });

    expect(mockDispatch).toHaveBeenCalledWith({ type: "socket/connect" });
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchConfig
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchMediaLists
    expect(mockDispatch).toHaveBeenCalledWith(expect.any(Function)); // fetchPersonalities

    // Verify fetchProviders was NOT called
    const dispatchCalls = mockDispatch.mock.calls;
    const hasProviderCall = dispatchCalls.some(call => {
      const action = call[0];
      return typeof action === 'function' && action.toString().includes('fetchProviders');
    });
    expect(hasProviderCall).toBe(false);
  });

  // Test specifically for the userSynced state transitions and effects on rendering
  it("transitions from loading spinner to content when API login completes and sets userSynced to true", async () => {
    // Mock auth and API, but don't resolve the API promise yet
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    const apiMock = apiModule.api;

    // Create a manually controllable promise
    let resolvePromise: (value: { status: string }) => void;
    const apiPromise = new Promise<{ status: string }>((resolve) => {
      resolvePromise = resolve;
    });
    (apiMock.post as vi.Mock).mockImplementation(() => apiPromise);

    // Create container for assertion
    const container = document.createElement('div');
    document.body.appendChild(container);

    // First render - should be in loading state
    await act(async () => {
      render(
        <Provider store={configureStore({
          reducer: {
            app: (state = {}) => state,
            socket: (state = { connected: true }) => state,
          },
        })}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<RootComponent />} />
            </Routes>
          </MemoryRouter>
        </Provider>,
        { container }
      );
    });

    // Verify we're in the loading state with the spinner
    expect(container.querySelector('[data-testid="spinner"]')).toBeInTheDocument();
    expect(container.querySelector('[data-testid="main-sidebar"]')).not.toBeInTheDocument();

    // Now resolve the API call, which should set userSynced to true
    await act(async () => {
      // Resolve promise which triggers userSynced to be set to true
      resolvePromise({ status: "success" });
      // Wait for the state update to propagate
      await new Promise(r => setTimeout(r, 0));
    });

    // Verify the transition - spinner should be gone, content should be visible
    expect(container.querySelector('[data-testid="spinner"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-testid="main-sidebar"]')).toBeInTheDocument();

    // Clean up
    document.body.removeChild(container);
  });
});
