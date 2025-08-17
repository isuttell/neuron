import { vi } from 'vitest';
import { api } from "../api";
import { getAccessToken } from "@/actions/getToken";
import { setCSRFToken, getCSRFToken, clearCSRFToken } from "../csrf";

// Mock the getAccessToken function
vi.mock("@/actions/getToken");

describe("ApiClient", () => {
  const mockToken = "test-token";
  const mockResponse = { data: "test" };

  beforeEach(() => {
    // Reset all mocks before each test
    vi.resetAllMocks();

    // Mock getAccessToken to return our test token
    (getAccessToken as vi.Mock).mockResolvedValue(mockToken);

    // Mock fetch globally
    global.fetch = vi.fn();

    // Clear CSRF token before each test
    clearCSRFToken();
  });

  afterEach(() => {
    vi.resetAllMocks();
    clearCSRFToken();
  });

  describe("GET requests", () => {
    it("should make a GET request with correct headers", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.get("/test");

      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        headers: {
          Authorization: `Bearer ${mockToken}`,
          "Content-Type": "application/json",
        },
        credentials: "include",
        signal: expect.any(AbortSignal),
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when GET request fails", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve({ error: "Not Found" }),
      });

      await expect(api.get("/test")).rejects.toThrow("Not Found");
    });
  });

  describe("POST requests", () => {
    const postData = { key: "value" };

    it("should make a POST request with correct headers and body", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.post("/test", postData);

      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${mockToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(postData),
        credentials: "include",
        signal: expect.any(AbortSignal),
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when POST request fails", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve({ error: "Bad Request" }),
      });

      await expect(api.post("/test", postData)).rejects.toThrow(
        "Bad Request"
      );
    });
  });

  describe("PUT requests", () => {
    const putData = { key: "value" };

    it("should make a PUT request with correct headers and body", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.put("/test", putData);

      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${mockToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(putData),
        credentials: "include",
        signal: expect.any(AbortSignal),
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when PUT request fails", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve({ error: "Bad Request" }),
      });

      await expect(api.put("/test", putData)).rejects.toThrow(
        "Bad Request"
      );
    });
  });

  describe("DELETE requests", () => {
    it("should make a DELETE request with correct headers", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.delete("/test");

      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${mockToken}`,
          "Content-Type": "application/json",
        },
        body: undefined,
        credentials: "include",
        signal: expect.any(AbortSignal),
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when DELETE request fails", async () => {
      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve({ error: "Not Found" }),
      });

      await expect(api.delete("/test")).rejects.toThrow("Not Found");
    });
  });

  describe("Error handling", () => {
    it("should handle network errors", async () => {
      (global.fetch as vi.Mock).mockRejectedValueOnce(
        new Error("Network error")
      );

      await expect(api.get("/test")).rejects.toThrow("Network error");
    });

    it("should handle token retrieval errors", async () => {
      const tokenError = new Error("Token error");
      (getAccessToken as vi.Mock).mockRejectedValueOnce(tokenError);

      await expect(api.get("/test")).rejects.toThrow("Token error");
    });

    it("should handle timeout errors with specific timeout duration", async () => {
      // Mock fetch to simulate a timeout by taking longer than the timeout duration
      (global.fetch as vi.Mock).mockImplementationOnce(() => {
        return new Promise((_, reject) => {
          setTimeout(() => {
            const abortError = new Error("The operation was aborted");
            abortError.name = "AbortError";
            reject(abortError);
          }, 75); // Longer than 50ms timeout to trigger the natural timeout
        });
      });

      try {
        await api.get("/test", { timeout: 50 }); // Short timeout to trigger abort
        fail("Should have thrown an error");
      } catch (error: unknown) {
        expect(error).toHaveProperty("message", "Request timed out after 50ms");
        expect(error).toHaveProperty("type", "network");
      }
    });

    it("should handle manual abort errors differently from timeout errors", async () => {
      const abortError = new Error("The operation was aborted");
      abortError.name = "AbortError";
      (global.fetch as vi.Mock).mockRejectedValueOnce(abortError);

      try {
        await api.get("/test");
        fail("Should have thrown an error");
      } catch (error: unknown) {
        expect(error).toHaveProperty("message", "Request was aborted");
        expect(error).toHaveProperty("type", "network");
      }
    });

    it("should handle timeout errors in POST requests with correct timeout duration", async () => {
      // Mock fetch to simulate a timeout
      (global.fetch as vi.Mock).mockImplementationOnce(() => {
        return new Promise((_, reject) => {
          setTimeout(() => {
            const abortError = new Error("The operation was aborted");
            abortError.name = "AbortError";
            reject(abortError);
          }, 150);
        });
      });

      try {
        await api.post("/test", { data: "test" }, { timeout: 100 });
        fail("Should have thrown an error");
      } catch (error: unknown) {
        expect(error).toHaveProperty("message", "Request timed out after 100ms");
        expect(error).toHaveProperty("type", "network");
      }
    });
  });

  describe("CSRF token handling", () => {
    const csrfToken = "test-csrf-token";

    it("should capture CSRF token from login response body", async () => {
      const loginResponse = {
        status: "success",
        user_id: "user123",
        csrf_token: csrfToken,
      };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(loginResponse),
      });

      // Make login request
      await api.post("/users/login", {});

      // Verify CSRF token was stored
      expect(getCSRFToken()).toBe(csrfToken);
    });

    it("should capture new_csrf_token from response body (legacy)", async () => {
      const responseWithNewToken = {
        data: "test",
        new_csrf_token: csrfToken,
      };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(responseWithNewToken),
      });

      await api.post("/test", {});

      expect(getCSRFToken()).toBe(csrfToken);
    });

    it("should capture CSRF token from X-New-CSRF-Token header (preferred)", async () => {
      const responseWithHeaderToken = { data: "test" };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([
          ["content-type", "application/json"],
          ["X-New-CSRF-Token", csrfToken],
        ]),
        json: () => Promise.resolve(responseWithHeaderToken),
      });

      await api.post("/test", {});

      expect(getCSRFToken()).toBe(csrfToken);
    });

    it("should prefer header token over body token", async () => {
      const headerToken = "header-csrf-token";
      const bodyToken = "body-csrf-token";

      const responseWithBothTokens = {
        data: "test",
        new_csrf_token: bodyToken,
        csrf_token: bodyToken,
      };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([
          ["content-type", "application/json"],
          ["X-New-CSRF-Token", headerToken],
        ]),
        json: () => Promise.resolve(responseWithBothTokens),
      });

      await api.post("/test", {});

      expect(getCSRFToken()).toBe(headerToken);
    });

    it("should include CSRF token in POST request headers when available", async () => {
      // Set up CSRF token
      setCSRFToken(csrfToken);

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      await api.post("/test", { data: "test" });

      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${mockToken}`,
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ data: "test" }),
        credentials: "include",
        signal: expect.any(AbortSignal),
      });
    });

    it("should include CSRF token in FormData for POST requests", async () => {
      // Set up CSRF token
      setCSRFToken(csrfToken);

      const formData = new FormData();
      formData.append("test", "value");

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      await api.post("/test", formData);

      // Check that fetch was called with FormData that includes CSRF token
      const fetchCall = (global.fetch as vi.Mock).mock.calls[0];
      const requestBody = fetchCall[1].body as FormData;

      expect(requestBody.get("csrf_token")).toBe(csrfToken);
      expect(requestBody.get("test")).toBe("value");
    });

    it("should store new CSRF token from error response", async () => {
      const newCsrfToken = "new-csrf-token";
      const errorResponse = {
        error: "Invalid request",
        new_csrf_token: newCsrfToken,
      };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400, // Use 400 to avoid CSRF retry logic
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(errorResponse),
      });

      try {
        await api.post("/test", {});
      } catch {
        // Error is expected, but token should still be stored
      }

      // New CSRF token should be stored even on error
      expect(getCSRFToken()).toBe(newCsrfToken);
    });

    it("should not overwrite existing CSRF token when response has no token", async () => {
      // Set initial CSRF token
      setCSRFToken(csrfToken);

      const responseWithoutToken = { data: "test" };

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(responseWithoutToken),
      });

      await api.post("/test", {});

      // Original token should remain
      expect(getCSRFToken()).toBe(csrfToken);
    });

    it("should replace existing CSRF token in FormData during retry", async () => {
      const oldToken = "old-csrf-token";
      const newToken = "new-csrf-token";

      // Set initial CSRF token
      setCSRFToken(oldToken);

      const formData = new FormData();
      formData.append("test", "value");
      formData.append("csrf_token", oldToken); // Simulate existing token

      // First call fails with CSRF error
      (global.fetch as vi.Mock)
        .mockResolvedValueOnce({
          ok: false,
          status: 403,
          headers: new Map([["content-type", "application/json"]]),
          json: () => Promise.resolve({
            error: "Forbidden",
            message: "CSRF validation failed",
            error_code: "CSRF_TOKEN_INVALID"
          }),
        })
        // Refresh CSRF call succeeds
        .mockResolvedValueOnce({
          ok: true,
          headers: new Map([["content-type", "application/json"]]),
          json: () => Promise.resolve({ csrf_token: newToken }),
        })
        // Retry succeeds
        .mockResolvedValueOnce({
          ok: true,
          headers: new Map([["content-type", "application/json"]]),
          json: () => Promise.resolve(mockResponse),
        });

      await api.post("/test", formData);

      // Verify the retry call used the new token
      const retryCalls = (global.fetch as vi.Mock).mock.calls;
      const retryCall = retryCalls[2]; // Third call is the retry
      const retryBody = retryCall[1].body as FormData;

      expect(retryBody.get("csrf_token")).toBe(newToken);
      expect(retryBody.get("test")).toBe("value");
    });

    it("should handle FormData with existing token when none was initially set", async () => {
      const existingToken = "existing-token";
      const newToken = "new-csrf-token";

      // No initial CSRF token set
      clearCSRFToken();

      // Create FormData with existing token (edge case)
      const formData = new FormData();
      formData.append("test", "value");
      formData.append("csrf_token", existingToken);

      // Set new token
      setCSRFToken(newToken);

      (global.fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        headers: new Map([["content-type", "application/json"]]),
        json: () => Promise.resolve(mockResponse),
      });

      await api.post("/test", formData);

      // Should replace the existing token with the new one
      const fetchCall = (global.fetch as vi.Mock).mock.calls[0];
      const requestBody = fetchCall[1].body as FormData;

      expect(requestBody.get("csrf_token")).toBe(newToken);
      expect(requestBody.get("test")).toBe("value");
    });
  });
});
