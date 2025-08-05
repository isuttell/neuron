/**
 * Centralized authentication error handler
 *
 * This module provides proper handling of Auth0 authentication errors following Auth0 best practices.
 * Different types of errors require different handling approaches:
 * - Auth0 SDK errors with recoverable codes should use loginWithRedirect()
 * - API 401 errors indicate server-side token validation failure and require page reload
 */

type LoginWithRedirect = (options?: { appState?: { returnTo?: string } }) => Promise<void>;

/**
 * Auth0 SDK error codes that are recoverable and should trigger loginWithRedirect
 */
const RECOVERABLE_AUTH0_ERRORS = [
  'login_required',
  'consent_required',
  'interaction_required',
  'mfa_required'
];

/**
 * Checks if an error is an API authentication error (401 from server)
 */
export function isApiAuthError(error: unknown): boolean {
  if (!error) return false;

  const apiError = error as { status?: number };
  return apiError.status === 401;
}

/**
 * Checks if an error is specifically a "User role required" error
 */
export function isUserRoleRequiredError(error: unknown): boolean {
  if (!error) return false;

  // Check multiple possible locations for the error message
  const apiError = error as Record<string, unknown>;
  const possibleMessages = [
    apiError.message,
    (apiError.data as Record<string, unknown>)?.message,
    (apiError.data as Record<string, unknown>)?.error,
    // For ClassifiedError objects, the message might be directly on the error
    error instanceof Error ? error.message : null,
    // Also check toString() as a fallback
    typeof error === 'object' && error !== null ? error.toString() : null
  ].filter(Boolean);

  return possibleMessages.some(msg =>
    typeof msg === 'string' && msg.includes('User role required')
  );
}

/**
 * Checks if an error is a recoverable Auth0 SDK error
 */
export function isRecoverableAuth0Error(error: unknown): boolean {
  if (!error) return false;

  // Check for Auth0 SDK error structure
  const auth0Error = error as { error?: string; message?: string };
  const errorCode = auth0Error.error;
  const errorMessage = auth0Error.message || (error instanceof Error ? error.message : '');

  // Check error code first (most reliable)
  if (errorCode && RECOVERABLE_AUTH0_ERRORS.includes(errorCode)) {
    return true;
  }

  // Fallback to message checking for older Auth0 versions
  return RECOVERABLE_AUTH0_ERRORS.some(pattern =>
    errorMessage.toLowerCase().includes(pattern)
  );
}

/**
 * Handles API authentication errors by reloading the page
 *
 * This is appropriate for 401 errors from the API which indicate
 * server-side token validation failure. However, "User role required"
 * errors should not trigger a reload as they indicate insufficient permissions
 * rather than authentication failure.
 */
export function handleApiAuthError(error: unknown): void {
  if (isApiAuthError(error)) {
    // Don't reload for "User role required" errors - let the app handle them through Redux
    if (isUserRoleRequiredError(error)) {
      return;
    }

    console.warn('API authentication error detected, reloading page to re-authenticate:', error);

    // Small delay to allow any pending operations to complete
    setTimeout(() => {
      window.location.reload();
    }, 100);
  }
}

/**
 * Handles Auth0 SDK authentication errors using loginWithRedirect
 *
 * This is the proper way to handle recoverable Auth0 errors according to Auth0 docs.
 */
export function handleAuth0Error(error: unknown, loginWithRedirect: LoginWithRedirect): void {
  if (isRecoverableAuth0Error(error)) {
    console.warn('Auth0 SDK error detected, redirecting to login:', error);

    loginWithRedirect({
      appState: { returnTo: window.location.pathname }
    }).catch(loginError => {
      console.error('Failed to redirect to login:', loginError);
      // Fallback to page reload if loginWithRedirect fails
      setTimeout(() => window.location.reload(), 100);
    });
  }
}

/**
 * Legacy function for backward compatibility
 * @deprecated Use handleApiAuthError or handleAuth0Error instead
 */
export function handleAuthError(error: unknown): void {
  // For now, just handle API auth errors to maintain existing behavior
  handleApiAuthError(error);
}

/**
 * Wrapper for async functions that automatically handles API auth errors
 */
export function withApiAuthErrorHandling<T extends unknown[], R>(
  fn: (...args: T) => Promise<R>
): (...args: T) => Promise<R> {
  return async (...args: T): Promise<R> => {
    try {
      return await fn(...args);
    } catch (error) {
      handleApiAuthError(error);
      throw error;
    }
  };
}
