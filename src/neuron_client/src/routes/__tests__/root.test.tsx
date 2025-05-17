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
jest.mock("@auth0/auth0-react", () => ({
  useAuth0: jest.fn(),
  withAuthenticationRequired: jest.fn((component) => component),
}));

// Mock API client
jest.mock("../../lib/api", () => ({
  api: {
    post: jest.fn(),
  },
}));

// Mock all the imported components
jest.mock("@/components/layout/MainSidebar", () => ({
  MainSidebar: () => <div data-testid="main-sidebar">MainSidebar</div>,
}));

jest.mock("@/components/ThreadTitleUpdater", () => ({
  ThreadTitleUpdater: () => <div>ThreadTitleUpdater</div>,
}));

jest.mock("@/components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

jest.mock("@/components/ui/sidebar", () => ({
  SidebarProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock dispatch and selector hooks
const mockDispatch = jest.fn();
const useAppDispatchMock = jest.spyOn(hooks, "useAppDispatch");
const useAppSelectorMock = jest.spyOn(hooks, "useAppSelector");

describe("RootComponent", () => {
  // Reset mocks before each test
  beforeEach(() => {
    jest.clearAllMocks();
    useAppDispatchMock.mockReturnValue(mockDispatch);
  });

  const mockGetAccessTokenSilently = jest.fn().mockResolvedValue("mock-token");

  // Setup auth0 mock with different states
  const setupAuth0Mock = (options: {
    isAuthenticated: boolean;
    isLoading: boolean;
    error?: Error | undefined;
  }) => {
    const { isAuthenticated, isLoading, error } = options;

    const useAuth0Mock = jest.spyOn(auth0React, "useAuth0");
    useAuth0Mock.mockReturnValue({
      isAuthenticated,
      isLoading,
      error,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      loginWithRedirect: jest.fn(),
      logout: jest.fn(),
      getAccessTokenWithPopup: jest.fn(),
      getIdTokenClaims: jest.fn(),
      loginWithPopup: jest.fn(),
      handleRedirectCallback: jest.fn(),
      user: { nickname: "testuser", picture: "https://example.com/avatar.png" } as User,
    } as Auth0ContextInterface<User>);
  };

  // Helper function to setup mock API responses
  const setupApiMock = (success: boolean = true) => {
    const apiMock = apiModule.api;
    if (success) {
      (apiMock.post as jest.Mock).mockResolvedValue({ status: "success" });
    } else {
      (apiMock.post as jest.Mock).mockRejectedValue(new Error("API error"));
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
    const loginWithRedirect = jest.fn();

    setupAuth0Mock({ isAuthenticated: false, isLoading: false });
    jest.spyOn(auth0React, "useAuth0").mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: undefined,
      loginWithRedirect,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      logout: jest.fn(),
      getAccessTokenWithPopup: jest.fn(),
      getIdTokenClaims: jest.fn(),
      loginWithPopup: jest.fn(),
      handleRedirectCallback: jest.fn(),
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

  it("keeps showing spinner when authenticated but not connected", async () => {
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    setupApiMock(true);

    // Connection status is false
    await act(async () => {
      renderComponent(false);
    });

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("main-sidebar")).not.toBeInTheDocument();
  });

  it("shows spinner when not fully synced with backend", async () => {
    // Create necessary mocks
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    const apiMock = apiModule.api;

    // Don't resolve the promise - keep it pending so userSynced stays false
    (apiMock.post as jest.Mock).mockImplementation(() => new Promise(() => {}));

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
  it("renders content only when authenticated, connected, and user is synced", async () => {
    // Mock auth and API
    setupAuth0Mock({ isAuthenticated: true, isLoading: false });
    const apiMock = apiModule.api;
    (apiMock.post as jest.Mock).mockResolvedValue({ status: "success" });

    // Mock state to simulate the userSynced state being true
    const useStateMock = jest.spyOn(React, 'useState');
    useStateMock.mockImplementationOnce(() => {
      return [true, jest.fn()]; // Simulate userSynced=true
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
    (apiMock.post as jest.Mock).mockImplementation(() => apiPromise);

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
