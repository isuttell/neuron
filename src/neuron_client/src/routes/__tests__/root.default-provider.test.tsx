import { render, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { useAuth0 } from "@auth0/auth0-react";
import { RootComponent } from "../root";
import appReducer from "@/slices/appSlice";
import providerReducer from "@/slices/providerSlice";
import socketReducer from "@/slices/socketSlice";
import mediaListsReducer from "@/slices/mediaListsSlice";
import mediaReducer from "@/slices/mediaSlice";
import messagesReducer from "@/slices/messagesSlice";
import threadsReducer from "@/slices/threadsSlice";
import personalitiesReducer from "@/slices/personalitiesSlice";
import imagesReducer from "@/slices/imagesSlice";
import promptsReducer from "@/slices/promptsSlice";
import embeddingsReducer from "@/slices/embeddingsSlice";
import schedulerReducer from "@/slices/schedulerSlice";
import usersReducer from "@/slices/usersSlice";

// Mock Auth0
jest.mock("@auth0/auth0-react");

// Mock SVG imports
jest.mock("@/assets/logo.svg", () => "logo.svg");

// Mock components that might have complex dependencies
jest.mock("@/components/layout/MainSidebar", () => ({
  MainSidebar: () => <div>MainSidebar</div>,
}));

jest.mock("@/components/ThreadTitleUpdater", () => ({
  ThreadTitleUpdater: () => null,
}));

// Mock API
jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { api } from "@/lib/api";

// Mock actions
jest.mock("@/actions/getToken", () => ({
  setGetAccessTokenSilently: jest.fn(),
}));

// Mock WebSocketManager
jest.mock("@/WebSocketManager", () => ({
  socketManager: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    emit: jest.fn(),
    on: jest.fn(),
    off: jest.fn(),
  },
}));

describe("Root Component - Default Provider Selection", () => {
  let store: ReturnType<typeof configureStore>;
  const mockGetAccessTokenSilently = jest.fn();

  beforeEach(() => {
    // Mock window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), // deprecated
        removeListener: jest.fn(), // deprecated
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
    store = configureStore({
      reducer: {
        app: appReducer,
        providers: providerReducer,
        socket: socketReducer,
        mediaLists: mediaListsReducer,
        media: mediaReducer,
        messages: messagesReducer,
        threads: threadsReducer,
        personalities: personalitiesReducer,
        images: imagesReducer,
        prompts: promptsReducer,
        embeddings: embeddingsReducer,
        scheduler: schedulerReducer,
        users: usersReducer,
      },
    });

    // Mock Auth0 as authenticated
    (useAuth0 as jest.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      loginWithRedirect: jest.fn(),
      logout: jest.fn(),
    });

    // Mock socket as connected
    store.dispatch({ type: "socket/connectionChanged", payload: true });

    jest.clearAllMocks();
  });

  it("should automatically set default provider when no active provider exists", async () => {
    const mockProviders = [
      {
        id: "provider-1",
        model_id: "gpt-4",
        provider: "openai",
        default: false,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "provider-2",
        model_id: "claude-3",
        provider: "anthropic",
        default: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ];

    // Mock API responses
    (api.get as jest.Mock).mockImplementation((url) => {
      if (url === "/providers/") {
        return Promise.resolve({
          providers: mockProviders,
          active_provider_id: null, // No active provider
        });
      }
      if (url === "/media/lists") {
        return Promise.resolve({
          media_lists: [],
          media_list_items: [],
          media_items: [],
        });
      }
      if (url === "/media/lists") {
        return Promise.resolve({
          media_lists: [],
          media_list_items: [],
          media_items: [],
        });
      }
      return Promise.resolve({});
    });

    (api.post as jest.Mock).mockResolvedValue({});

    render(
      <Provider store={store}>
        <MemoryRouter>
          <RootComponent />
        </MemoryRouter>
      </Provider>
    );

    // Wait for providers to be fetched
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/providers/");
    });

    // Wait for setupProvider to be called with the default provider
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/providers/provider-2/activate", {});
    });
  });

  it("should not set default provider when active provider exists", async () => {
    const mockProviders = [
      {
        id: "provider-1",
        model_id: "gpt-4",
        provider: "openai",
        default: false,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "provider-2",
        model_id: "claude-3",
        provider: "anthropic",
        default: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ];

    // Mock API responses
    (api.get as jest.Mock).mockImplementation((url) => {
      if (url === "/providers/") {
        return Promise.resolve({
          providers: mockProviders,
          active_provider_id: "provider-1", // Active provider exists
        });
      }
      if (url === "/media/lists") {
        return Promise.resolve({
          media_lists: [],
          media_list_items: [],
          media_items: [],
        });
      }
      return Promise.resolve({});
    });

    (api.post as jest.Mock).mockResolvedValue({});

    render(
      <Provider store={store}>
        <MemoryRouter>
          <RootComponent />
        </MemoryRouter>
      </Provider>
    );

    // Wait for providers to be fetched
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/providers/");
    });

    // setupProvider should NOT be called since there's already an active provider
    await waitFor(() => {
      expect(api.post).not.toHaveBeenCalledWith(expect.stringContaining("/providers/"), expect.any(Object));
    });
  });

  it("should not set provider when no default provider exists", async () => {
    const mockProviders = [
      {
        id: "provider-1",
        model_id: "gpt-4",
        provider: "openai",
        default: false,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "provider-2",
        model_id: "claude-3",
        provider: "anthropic",
        default: false, // No default provider
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ];

    // Mock API responses
    (api.get as jest.Mock).mockImplementation((url) => {
      if (url === "/providers/") {
        return Promise.resolve({
          providers: mockProviders,
          active_provider_id: null,
        });
      }
      if (url === "/media/lists") {
        return Promise.resolve({
          media_lists: [],
          media_list_items: [],
          media_items: [],
        });
      }
      return Promise.resolve({});
    });

    (api.post as jest.Mock).mockResolvedValue({});

    render(
      <Provider store={store}>
        <MemoryRouter>
          <RootComponent />
        </MemoryRouter>
      </Provider>
    );

    // Wait for providers to be fetched
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/providers/");
    });

    // setupProvider should NOT be called since there's no default provider
    await waitFor(() => {
      expect(api.post).not.toHaveBeenCalledWith(expect.stringContaining("/providers/"), expect.any(Object));
    });
  });
});
