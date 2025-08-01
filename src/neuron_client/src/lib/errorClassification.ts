import type { SerializableError } from "../types/error";

// UI error types for different error handling strategies
export type UIErrorType = 'not_found' | 'auth_error' | 'network_error' | 'client_error' | 'server_error';

/**
 * Generic error classification utility for UI error handling
 *
 * Converts various error types into standardized UI error types that can be used
 * consistently across components for error display and handling strategies.
 */
export class ErrorClassifier {
  /**
   * Classifies a SerializableError into a UI error type
   *
   * @param error - The serializable error object to classify
   * @returns UI error type or null if no error
   */
  static classifySerializableError(error: SerializableError | null): UIErrorType | null {
    if (!error) return null;

    // Check for specific status codes first (most reliable)
    if (error.status === 404 || error.type === 'not_found') {
      return 'not_found';
    }

    if (error.status === 401 || error.status === 403 || error.type === 'auth') {
      return 'auth_error';
    }

    if (error.type === 'network') {
      return 'network_error';
    }

    // Client errors (4xx)
    if (error.status && error.status >= 400 && error.status < 500) {
      return 'client_error';
    }

    // Server errors (5xx)
    if (error.status && error.status >= 500) {
      return 'server_error';
    }

    // Fallback based on error type
    if (error.type) {
      switch (error.type) {
        case 'client_error':
          return 'client_error';
        case 'server':
          return 'server_error';
        default:
          return 'server_error'; // Safe default to show error UI
      }
    }

    return 'server_error'; // Safe default
  }

  /**
   * Classifies a legacy string error into a UI error type
   *
   * @param error - The string error to classify
   * @returns UI error type or null if no error
   */
  static classifyStringError(error: string | null): UIErrorType | null {
    if (!error) return null;

    const errorLower = error.toLowerCase();

    // Check for specific patterns in error messages
    if (error.includes('404') ||
        errorLower.includes('not found') ||
        errorLower.includes('resource not found')) {
      return 'not_found';
    }

    if (error.includes('401') || error.includes('403') ||
        errorLower.includes('authentication') ||
        errorLower.includes('unauthorized') ||
        errorLower.includes('forbidden')) {
      return 'auth_error';
    }

    if (errorLower.includes('network') ||
        errorLower.includes('timeout') ||
        errorLower.includes('connection failed')) {
      return 'network_error';
    }

    if (error.includes('500') || error.includes('502') || error.includes('503') ||
        errorLower.includes('server error') ||
        errorLower.includes('internal server')) {
      return 'server_error';
    }

    // Default to server_error to ensure error UI is shown
    return 'server_error';
  }

  /**
   * Classifies multiple errors with priority order
   *
   * Processes errors in order of specificity:
   * 1. SerializableError objects (most reliable)
   * 2. String errors (fallback for legacy systems)
   *
   * @param errors - Array of mixed error types to classify
   * @returns The first non-null UI error type found, or null if no errors
   */
  static classifyErrors(...errors: Array<SerializableError | string | null | undefined>): UIErrorType | null {
    // Process SerializableError objects first (most reliable)
    for (const error of errors) {
      if (error && typeof error === 'object' && 'type' in error) {
        const result = this.classifySerializableError(error as SerializableError);
        if (result) return result;
      }
    }

    // Process string errors as fallback
    for (const error of errors) {
      if (error && typeof error === 'string') {
        const result = this.classifyStringError(error);
        if (result) return result;
      }
    }

    return null;
  }

  /**
   * Checks if any of the provided errors indicate an error state
   *
   * @param errors - Array of mixed error types to check
   * @returns true if any error exists, false otherwise
   */
  static hasError(...errors: Array<SerializableError | string | null | undefined>): boolean {
    return errors.some(error =>
      (error && typeof error === 'object' && 'type' in error) ||
      (error && typeof error === 'string')
    );
  }
}

/**
 * Convenience function for classifying errors in components
 *
 * @param errors - Mixed error types to classify
 * @returns UI error type or null
 */
export function classifyErrors(...errors: Array<SerializableError | string | null | undefined>): UIErrorType | null {
  return ErrorClassifier.classifyErrors(...errors);
}

/**
 * Convenience function for checking if errors exist
 *
 * @param errors - Mixed error types to check
 * @returns true if any error exists
 */
export function hasError(...errors: Array<SerializableError | string | null | undefined>): boolean {
  return ErrorClassifier.hasError(...errors);
}
