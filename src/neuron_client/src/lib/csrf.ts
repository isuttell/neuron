/**
 * CSRF token management for Neuron
 *
 * This module handles storing and retrieving CSRF tokens received from the login endpoint.
 * The CSRF token should be included in all state-changing requests (POST, PUT, DELETE, PATCH).
 */

const CSRF_TOKEN_KEY = "neuron_csrf_token";

/**
 * Store CSRF token received from login response
 */
export function setCSRFToken(token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(CSRF_TOKEN_KEY, token);
  }
}

/**
 * Get stored CSRF token
 */
export function getCSRFToken(): string | null {
  if (typeof window !== "undefined") {
    return sessionStorage.getItem(CSRF_TOKEN_KEY);
  }
  return null;
}

/**
 * Clear CSRF token (on logout)
 */
export function clearCSRFToken(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(CSRF_TOKEN_KEY);
  }
}

/**
 * Add CSRF token to headers if available
 */
export function addCSRFHeader(headers: HeadersInit): HeadersInit {
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    return {
      ...headers,
      "X-CSRF-Token": csrfToken,
    };
  }
  return headers;
}

/**
 * Add CSRF token to FormData if available
 */
export function addCSRFToFormData(formData: FormData): FormData {
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    formData.delete("csrf_token");
    formData.append("csrf_token", csrfToken);
  }
  return formData;
}
