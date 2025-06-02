import { getAccessToken } from "@/actions/getToken";
import { addCSRFHeader, addCSRFToFormData, setCSRFToken, clearCSRFToken } from "./csrf";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };
type RequestData = Record<string, JsonValue> | FormData;

interface ApiError {
  error?: string;
  message?: string;
  new_csrf_token?: string;
}

class ApiClient {
  private baseUrl: string = "/api";
  private maxRetries: number = 1; // One retry for CSRF errors

  private async getHeaders(isFormData = false, includeCSRF = false): Promise<HeadersInit> {
    const accessToken = await getAccessToken();
    let headers: HeadersInit = {
      Authorization: `Bearer ${accessToken}`,
    };
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }
    // Add CSRF token for state-changing requests
    if (includeCSRF) {
      headers = addCSRFHeader(headers);
    }
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get("content-type");
    const isJson = contentType && contentType.includes("application/json");

    if (!response.ok) {
      if (isJson) {
        const errorData: ApiError = await response.json();

        // Handle new CSRF token if provided (from token rotation)
        if (errorData.new_csrf_token) {
          setCSRFToken(errorData.new_csrf_token);
        }

        // Create error with details
        const error = new Error(errorData.message || errorData.error || `API Error: ${response.statusText}`);
        (error as unknown as { status: number; data: ApiError }).status = response.status;
        (error as unknown as { status: number; data: ApiError }).data = errorData;
        throw error;
      }
      throw new Error(`API Error: ${response.statusText}`);
    }

    const data = await response.json();

    // Handle new CSRF token from response headers (preferred) or body (legacy)
    const newTokenFromHeader = response.headers.get("X-New-CSRF-Token");
    if (newTokenFromHeader) {
      setCSRFToken(newTokenFromHeader);
    } else if (data.new_csrf_token) {
      // Fallback to body for backward compatibility
      setCSRFToken(data.new_csrf_token);
    } else if (data.csrf_token) {
      // Handle CSRF token from login response
      setCSRFToken(data.csrf_token);
    }

    return data;
  }

  private async refreshCSRFToken(): Promise<void> {
    try {
      // Try to get a new CSRF token by calling a lightweight endpoint
      const response = await fetch(`${this.baseUrl}/auth/refresh-csrf`, {
        method: "POST",
        headers: await this.getHeaders(),
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data.csrf_token) {
          setCSRFToken(data.csrf_token);
        }
      }
    } catch (error) {
      console.error("Failed to refresh CSRF token:", error);
    }
  }

  private async fetchWithCSRF<T>(
    url: string,
    options: RequestInit,
    retryCount = 0
  ): Promise<T> {
    try {
      const response = await fetch(url, options);
      return await this.handleResponse<T>(response);
    } catch (error: unknown) {
      // Check if it's a CSRF error and we haven't exceeded retry limit
      const apiError = error as { status?: number; data?: { error?: string } };
      if (
        apiError.status === 403 &&
        apiError.data?.error?.includes("CSRF") &&
        retryCount < this.maxRetries
      ) {
        console.warn("CSRF token error, attempting to refresh...");

        // Clear the old token
        clearCSRFToken();

        // Try to refresh the CSRF token
        await this.refreshCSRFToken();

        // Retry the request with new headers
        const headers = await this.getHeaders(
          options.body instanceof FormData,
          ["POST", "PUT", "DELETE", "PATCH"].includes(options.method || "GET")
        );

        // Update headers in options
        options.headers = headers;

        // If it's FormData, we need to re-add the CSRF token
        if (options.body instanceof FormData) {
          options.body = addCSRFToFormData(options.body);
        }

        // Retry the request
        return this.fetchWithCSRF<T>(url, options, retryCount + 1);
      }

      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers,
      credentials: "include",
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data: RequestData): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers = await this.getHeaders(isFormData, true); // Include CSRF
    let body: string | FormData;

    if (isFormData) {
      // Add CSRF token to FormData
      body = addCSRFToFormData(data);
    } else {
      body = JSON.stringify(data);
    }

    return this.fetchWithCSRF<T>(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers,
      body,
      credentials: "include",
    });
  }

  async put<T>(endpoint: string, data: RequestData): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers = await this.getHeaders(isFormData, true); // Include CSRF
    let body: string | FormData;

    if (isFormData) {
      // Add CSRF token to FormData
      body = addCSRFToFormData(data);
    } else {
      body = JSON.stringify(data);
    }

    return this.fetchWithCSRF<T>(`${this.baseUrl}${endpoint}`, {
      method: "PUT",
      headers,
      body,
      credentials: "include",
    });
  }

  async patch<T>(endpoint: string, data: RequestData): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers = await this.getHeaders(isFormData, true); // Include CSRF
    let body: string | FormData;

    if (isFormData) {
      // Add CSRF token to FormData
      body = addCSRFToFormData(data);
    } else {
      body = JSON.stringify(data);
    }

    return this.fetchWithCSRF<T>(`${this.baseUrl}${endpoint}`, {
      method: "PATCH",
      headers,
      body,
      credentials: "include",
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders(false, true); // Include CSRF

    return this.fetchWithCSRF<T>(`${this.baseUrl}${endpoint}`, {
      method: "DELETE",
      headers,
      credentials: "include",
    });
  }
}

export const api = new ApiClient();
