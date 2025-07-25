import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  isApiAuthError,
  isRecoverableAuth0Error,
  handleApiAuthError,
  handleAuth0Error,
  withApiAuthErrorHandling
} from '../authErrorHandler';

// Mock window.location.reload
const mockReload = vi.fn();
Object.defineProperty(window, 'location', {
  value: {
    reload: mockReload,
    pathname: '/test',
  },
  writable: true,
});

// Mock loginWithRedirect
const mockLoginWithRedirect = vi.fn().mockResolvedValue(undefined);

describe('authErrorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('isApiAuthError', () => {
    it('returns true for 401 status errors', () => {
      const error = { status: 401, message: 'Unauthorized' };
      expect(isApiAuthError(error)).toBe(true);
    });

    it('returns false for non-401 errors', () => {
      const testCases = [
        { status: 500, message: 'Internal Server Error' },
        { status: 404, message: 'Not Found' },
        { message: 'Network error' },
        new Error('Something went wrong'),
        null,
        undefined,
      ];

      testCases.forEach(errorCase => {
        expect(isApiAuthError(errorCase)).toBe(false);
      });
    });
  });

  describe('isRecoverableAuth0Error', () => {
    it('returns true for Auth0 error codes', () => {
      const testCases = [
        { error: 'login_required' },
        { error: 'consent_required' },
        { error: 'interaction_required' },
        { error: 'mfa_required' },
      ];

      testCases.forEach(errorCase => {
        expect(isRecoverableAuth0Error(errorCase)).toBe(true);
      });
    });

    it('returns true for Error objects with auth-related messages', () => {
      const error = new Error('login_required');
      expect(isRecoverableAuth0Error(error)).toBe(true);
    });

    it('returns false for non-Auth0 errors', () => {
      const testCases = [
        { status: 401, message: 'Unauthorized' },
        { error: 'invalid_grant' },
        { message: 'Network error' },
        new Error('Something went wrong'),
        null,
        undefined,
      ];

      testCases.forEach(errorCase => {
        expect(isRecoverableAuth0Error(errorCase)).toBe(false);
      });
    });
  });

  describe('handleApiAuthError', () => {
    it('reloads the page for API auth errors', () => {
      const error = { status: 401, message: 'Unauthorized' };

      handleApiAuthError(error);

      // Fast-forward the timeout
      vi.advanceTimersByTime(100);

      expect(mockReload).toHaveBeenCalledOnce();
    });

    it('does not reload the page for non-auth errors', () => {
      const error = { status: 500, message: 'Internal Server Error' };

      handleApiAuthError(error);

      // Fast-forward the timeout
      vi.advanceTimersByTime(100);

      expect(mockReload).not.toHaveBeenCalled();
    });

    it('uses a small delay before reloading', () => {
      const error = { status: 401, message: 'Unauthorized' };

      handleApiAuthError(error);

      // Should not reload immediately
      expect(mockReload).not.toHaveBeenCalled();

      // Should reload after delay
      vi.advanceTimersByTime(100);
      expect(mockReload).toHaveBeenCalledOnce();
    });
  });

  describe('handleAuth0Error', () => {
    it('calls loginWithRedirect for recoverable Auth0 errors', () => {
      const error = { error: 'login_required' };

      handleAuth0Error(error, mockLoginWithRedirect);

      expect(mockLoginWithRedirect).toHaveBeenCalledWith({
        appState: { returnTo: '/test' }
      });
    });

    it('does not call loginWithRedirect for non-recoverable errors', () => {
      const error = { status: 500, message: 'Internal Server Error' };

      handleAuth0Error(error, mockLoginWithRedirect);

      expect(mockLoginWithRedirect).not.toHaveBeenCalled();
    });

    it('falls back to page reload if loginWithRedirect fails', async () => {
      const error = { error: 'login_required' };
      mockLoginWithRedirect.mockRejectedValue(new Error('Login failed'));

      handleAuth0Error(error, mockLoginWithRedirect);

      // Wait for the async operation to complete
      await vi.waitFor(() => {
        expect(mockLoginWithRedirect).toHaveBeenCalled();
      });

      // Fast-forward the fallback timeout
      vi.advanceTimersByTime(100);
      expect(mockReload).toHaveBeenCalledOnce();
    });
  });

  describe('withApiAuthErrorHandling', () => {
    it('wraps async functions with API auth error handling', async () => {
      const mockFn = vi.fn().mockResolvedValue('success');
      const wrappedFn = withApiAuthErrorHandling(mockFn);

      const result = await wrappedFn('arg1', 'arg2');

      expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
      expect(result).toBe('success');
      expect(mockReload).not.toHaveBeenCalled();
    });

    it('handles API auth errors and still throws', async () => {
      const authError = { status: 401, message: 'Unauthorized' };
      const mockFn = vi.fn().mockRejectedValue(authError);
      const wrappedFn = withApiAuthErrorHandling(mockFn);

      await expect(wrappedFn()).rejects.toEqual(authError);

      // Should trigger page reload
      vi.advanceTimersByTime(100);
      expect(mockReload).toHaveBeenCalledOnce();
    });

    it('does not handle non-auth errors', async () => {
      const nonAuthError = { status: 500, message: 'Internal Server Error' };
      const mockFn = vi.fn().mockRejectedValue(nonAuthError);
      const wrappedFn = withApiAuthErrorHandling(mockFn);

      await expect(wrappedFn()).rejects.toEqual(nonAuthError);

      // Should not trigger page reload
      vi.advanceTimersByTime(100);
      expect(mockReload).not.toHaveBeenCalled();
    });
  });
});
