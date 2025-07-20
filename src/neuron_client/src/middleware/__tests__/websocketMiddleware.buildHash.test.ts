import { configureStore } from '@reduxjs/toolkit';
import { toast } from 'sonner';
import websocketMiddleware from '../websocketMiddleware';
import appSlice, { getBuildHashMismatch } from '../../slices/appSlice';
import WebSocketManager from '../../WebSocketManager';
import { getCurrentBuildHash } from '../../utils/buildHash';

// Mock dependencies
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    dismiss: vi.fn(),
  },
}));

vi.mock('../../utils/buildHash', () => ({
  getCurrentBuildHash: vi.fn(),
}));

// Mock WebSocketManager
const mockWebSocketManager = {
  connect: vi.fn(),
  on: vi.fn(),
  onInternal: vi.fn(),
  close: vi.fn(),
  sendMessage: vi.fn(),
} as unknown as WebSocketManager;

describe('websocketMiddleware build hash handling', () => {
  let store: ReturnType<typeof configureStore>;
  let middleware: ReturnType<typeof websocketMiddleware>;

  beforeEach(() => {
    vi.clearAllMocks();

    store = configureStore({
      reducer: {
        app: appSlice,
        socket: (state = { connected: false, socket: null }, action) => {
          if (action.type === 'socket/connect') {
            return { ...state, connected: true, socket: action.payload };
          }
          return state;
        },
        messages: (state = { messages: [] }) => state,
        media: (state = { media: [] }) => state,
        threads: (state = { threads: [] }) => state,
        images: (state = { images: [] }) => state,
        prompts: (state = { prompts: [] }) => state,
        personalities: (state = { personalities: [] }) => state,
      },
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(websocketMiddleware(mockWebSocketManager)),
    });

    middleware = websocketMiddleware(mockWebSocketManager);
  });

  it('registers ping event handler when connecting', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);

    store.dispatch({ type: 'socket/connect' });

    // Verify that the ping handler was registered
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('ping', expect.any(Function));
  });

  it('detects hash mismatch when current hash differs from server hash', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);
    (getCurrentBuildHash as any).mockReturnValue('CLIENT123');

    store.dispatch({ type: 'socket/connect' });

    // Get the ping handler that was registered
    const pingHandler = (mockWebSocketManager.on as any).mock.calls.find(
      (call: any) => call[0] === 'ping'
    )[1];

    // Simulate receiving a ping with different hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
      static_hash: 'SERVER456',
    });

    // Check that build hash mismatch was detected
    const state = store.getState();
    expect(getBuildHashMismatch(state)).toBe(true);
  });

  it('does not detect mismatch when hashes match', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);
    (getCurrentBuildHash as any).mockReturnValue('SAME123');

    store.dispatch({ type: 'socket/connect' });

    const pingHandler = (mockWebSocketManager.on as any).mock.calls.find(
      (call: any) => call[0] === 'ping'
    )[1];

    // Simulate receiving a ping with same hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
      static_hash: 'SAME123',
    });

    // Check that no mismatch was detected
    const state = store.getState();
    expect(getBuildHashMismatch(state)).toBe(false);
  });

  it('does not detect mismatch when server provides no hash', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);
    (getCurrentBuildHash as any).mockReturnValue('CLIENT123');

    store.dispatch({ type: 'socket/connect' });

    const pingHandler = (mockWebSocketManager.on as any).mock.calls.find(
      (call: any) => call[0] === 'ping'
    )[1];

    // Simulate receiving a ping without static_hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
    });

    // Check that no mismatch was detected
    const state = store.getState();
    expect(getBuildHashMismatch(state)).toBe(false);
  });

  it('does not detect mismatch when client has no hash', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);
    (getCurrentBuildHash as any).mockReturnValue(null);

    store.dispatch({ type: 'socket/connect' });

    const pingHandler = (mockWebSocketManager.on as any).mock.calls.find(
      (call: any) => call[0] === 'ping'
    )[1];

    // Simulate receiving a ping with server hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
      static_hash: 'SERVER456',
    });

    // Check that no mismatch was detected (client has no hash to compare)
    const state = store.getState();
    expect(getBuildHashMismatch(state)).toBe(false);
  });

  it('handles multiple ping events correctly', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);
    (getCurrentBuildHash as any).mockReturnValue('CLIENT123');

    store.dispatch({ type: 'socket/connect' });

    const pingHandler = (mockWebSocketManager.on as any).mock.calls.find(
      (call: any) => call[0] === 'ping'
    )[1];

    // First ping - matching hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
      static_hash: 'CLIENT123',
    });

    expect(getBuildHashMismatch(store.getState())).toBe(false);

    // Second ping - different hash
    pingHandler({
      type: 'ping',
      timestamp: Date.now(),
      static_hash: 'SERVER456',
    });

    expect(getBuildHashMismatch(store.getState())).toBe(true);
  });

  it('registers all expected event handlers on connect', () => {
    (mockWebSocketManager.connect as any).mockReturnValue(true);

    store.dispatch({ type: 'socket/connect' });

    // Verify all event handlers are registered including ping
    const expectedEvents = [
      'message',
      'media',
      'partial_message',
      'thread',
      'sidebar_image',
      'prompt',
      'ping',
      'personality',
      'image',
    ];

    expectedEvents.forEach(event => {
      expect(mockWebSocketManager.on).toHaveBeenCalledWith(event, expect.any(Function));
    });
  });
});
