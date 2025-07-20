import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { toast } from 'sonner';
import { AppUpdateNotification } from '../AppUpdateNotification';
import appSlice from '../../slices/appSlice';

// Import the constant used by the component
const AUTO_RELOAD_DELAY_MS = 60 * 60 * 1000; // 1 hour

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    warning: vi.fn(),
    dismiss: vi.fn(),
  },
}));

// Mock window.location.reload
const mockReload = vi.fn();
Object.defineProperty(window, 'location', {
  value: {
    reload: mockReload,
  },
  writable: true,
});

// Mock setTimeout and clearTimeout
vi.useFakeTimers();
const mockSetTimeout = vi.spyOn(global, 'setTimeout');
const mockClearTimeout = vi.spyOn(global, 'clearTimeout');

const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      app: appSlice,
    },
    preloadedState: {
      app: {
        sidebar_image: "",
        isLoading: false,
        error: null,
        currentUser: null,
        favoritePersonalitiesCollapsed: true,
        buildHashMismatch: false,
        ...initialState,
      },
    },
  });
};

describe('AppUpdateNotification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    mockSetTimeout.mockClear();
    mockClearTimeout.mockClear();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
  });

  it('renders without crashing', () => {
    const store = createTestStore();
    render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );
  });

  it('does not show notification when no hash mismatch', () => {
    const store = createTestStore({
      buildHashMismatch: false,
    });

    render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    expect(toast.warning).not.toHaveBeenCalled();
  });


  it('shows notification when hash mismatch detected', () => {
    const store = createTestStore({
      buildHashMismatch: true,
    });

    render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    expect(toast.warning).toHaveBeenCalledWith("Update Available", expect.objectContaining({
      duration: Infinity,
      closeButton: true,
    }));
  });

  it('schedules auto-reload when notification is shown', async () => {
    const store = createTestStore({
      buildHashMismatch: true,
    });

    render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    // Wait for effects to run
    await vi.waitFor(() => {
      expect(mockSetTimeout).toHaveBeenCalled();
    });

    // Check that setTimeout was called with 1 hour
    expect(mockSetTimeout).toHaveBeenCalledWith(expect.any(Function), AUTO_RELOAD_DELAY_MS);
  });


  it('reloads page after timeout', async () => {
    const store = createTestStore({
      buildHashMismatch: true,
    });

    const { unmount } = render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    // Wait for effects to run first
    await vi.waitFor(() => {
      expect(mockSetTimeout).toHaveBeenCalled();
    });

    // Get the timeout function that was registered and call it directly
    const timeoutFn = mockSetTimeout.mock.calls[0][0];
    timeoutFn();

    expect(mockReload).toHaveBeenCalled();

    // Clean up
    unmount();
  });

  it('cleans up timeout on unmount', async () => {
    const store = createTestStore({
      buildHashMismatch: true,
    });

    const { unmount } = render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    // Wait for effects to run
    await vi.waitFor(() => {
      expect(mockSetTimeout).toHaveBeenCalled();
    });

    // Unmount component
    unmount();

    // Fast-forward time - reload should not happen because timer was cleared
    vi.advanceTimersByTime(AUTO_RELOAD_DELAY_MS);
    expect(mockReload).not.toHaveBeenCalled();
  });

  it('includes refresh button in toast description', () => {
    const store = createTestStore({
      buildHashMismatch: true,
    });

    render(
      <Provider store={store}>
        <AppUpdateNotification />
      </Provider>
    );

    const toastCall = (toast.warning as any).mock.calls[0];
    const toastConfig = toastCall[1];

    expect(toastConfig.description).toBeDefined();
    // The description contains JSX with button, which we can't easily test here
    // but we can verify the toast was called with the right structure
    expect(toastConfig.duration).toBe(Infinity);
    expect(toastConfig.closeButton).toBe(true);
  });
});
