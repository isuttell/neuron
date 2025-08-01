import type { ErrorType, ClassifiedError } from "@/lib/api";

// API Error interface (already serializable)
export interface ApiError {
  error?: string;
  message?: string;
  new_csrf_token?: string;
  error_code?: string;
  error_type?: string;
  retry_possible?: boolean;
}

// Serializable error interface for Redux state
export interface SerializableError {
  message: string;
  type: ErrorType;
  status?: number;
  data?: ApiError;
}

// Utility function to convert ClassifiedError to SerializableError
export function toSerializableError(error: ClassifiedError): SerializableError {
  return {
    message: error.message,
    type: error.type,
    status: error.status,
    data: error.data,
  };
}

// Type guard to check if an error is a ClassifiedError
export function isClassifiedError(error: unknown): error is ClassifiedError {
  return error instanceof Error && 'type' in error && 'status' in error;
}
