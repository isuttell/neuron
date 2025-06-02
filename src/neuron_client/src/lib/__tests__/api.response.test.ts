import { api } from "../api";
import { getAccessToken } from "@/actions/getToken";
import { addCSRFHeader, setCSRFToken } from "../csrf";

// Mock dependencies
jest.mock("@/actions/getToken", () => ({
  getAccessToken: jest.fn(),
}));

jest.mock("../csrf", () => ({
  addCSRFHeader: jest.fn((headers) => ({ ...headers, "X-CSRF-Token": "test-csrf-token" })),
  addCSRFToFormData: jest.fn((formData) => formData),
  setCSRFToken: jest.fn(),
  clearCSRFToken: jest.fn(),
}));

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("api client response handling", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getAccessToken as jest.Mock).mockResolvedValue("test-token");
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("response data extraction", () => {
    it("should return parsed JSON data directly, not wrapped in a data property", async () => {
      const mockResponseData = { id: "123", name: "Test" };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => mockResponseData,
      });

      const result = await api.get<typeof mockResponseData>("/test");

      expect(result).toEqual(mockResponseData);
      expect(result).not.toHaveProperty("data");
    });

    it("should handle array responses correctly", async () => {
      const mockArrayData = [{ id: "1" }, { id: "2" }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => mockArrayData,
      });

      const result = await api.get<typeof mockArrayData>("/test");

      expect(result).toEqual(mockArrayData);
      expect(Array.isArray(result)).toBe(true);
    });

    it("should handle nested object responses", async () => {
      const mockNestedData = {
        personalities: [{ id: "1", name: "Test" }],
        total: 1,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => mockNestedData,
      });

      const result = await api.get<typeof mockNestedData>("/test");

      expect(result).toEqual(mockNestedData);
      expect(result.personalities).toHaveLength(1);
      expect(result.total).toBe(1);
    });
  });

  describe("CSRF token handling", () => {
    it("should extract and set CSRF token from response headers", async () => {
      const newToken = "new-csrf-token-from-header";
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({
          "content-type": "application/json",
          "X-New-CSRF-Token": newToken,
        }),
        json: async () => ({ message: "success" }),
      });

      await api.post("/test", { data: "test" });

      expect(setCSRFToken).toHaveBeenCalledWith(newToken);
    });

    it("should extract CSRF token from response body if not in headers", async () => {
      const newToken = "new-csrf-token-from-body";
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ message: "success", new_csrf_token: newToken }),
      });

      await api.post("/test", { data: "test" });

      expect(setCSRFToken).toHaveBeenCalledWith(newToken);
    });

    it("should handle login response with csrf_token field", async () => {
      const loginToken = "login-csrf-token";
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          access_token: "new-access-token",
          csrf_token: loginToken,
        }),
      });

      await api.post("/auth/login", { email: "test@example.com", password: "password" });

      expect(setCSRFToken).toHaveBeenCalledWith(loginToken);
    });
  });

  describe("error response handling", () => {
    it("should throw error with message from API error response", async () => {
      const errorMessage = "Invalid request";
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ message: errorMessage }),
      });

      await expect(api.get("/test")).rejects.toThrow(errorMessage);
    });

    it("should throw error with error field if message is not present", async () => {
      const errorText = "Something went wrong";
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ error: errorText }),
      });

      await expect(api.post("/test", {})).rejects.toThrow(errorText);
    });

    it("should include status and data in error object", async () => {
      const errorData = { error: "Forbidden", code: "FORBIDDEN" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: "Forbidden",
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => errorData,
      });

      try {
        await api.delete("/test");
        fail("Should have thrown an error");
      } catch (error: unknown) {
        const apiError = error as { status: number; data: typeof errorData };
        expect(apiError.status).toBe(403);
        expect(apiError.data).toEqual(errorData);
      }
    });
  });

  describe("HTTP methods", () => {
    it("GET requests should not include CSRF token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true }),
      });

      await api.get("/test");

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/test",
        expect.objectContaining({
          headers: expect.not.objectContaining({
            "X-CSRF-Token": expect.any(String),
          }),
        })
      );
    });

    it("POST requests should include CSRF token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true }),
      });

      await api.post("/test", { data: "test" });

      expect(addCSRFHeader).toHaveBeenCalled();
    });

    it("PUT requests should include CSRF token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true }),
      });

      await api.put("/test", { data: "test" });

      expect(addCSRFHeader).toHaveBeenCalled();
    });

    it("DELETE requests should include CSRF token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true }),
      });

      await api.delete("/test");

      expect(addCSRFHeader).toHaveBeenCalled();
    });
  });
});
