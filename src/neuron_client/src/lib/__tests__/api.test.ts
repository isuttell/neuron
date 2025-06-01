import { api } from "../api";
import { getAccessToken } from "@/actions/getToken";

// Mock the getAccessToken function
jest.mock("@/actions/getToken");

describe("ApiClient", () => {
  const mockToken = "test-token";
  const mockResponse = { data: "test" };

  beforeEach(() => {
    // Reset all mocks before each test
    jest.resetAllMocks();

    // Mock getAccessToken to return our test token
    (getAccessToken as jest.Mock).mockResolvedValue(mockToken);

    // Mock fetch globally
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe("GET requests", () => {
    it("should make a GET request with correct headers", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when GET request fails", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when POST request fails", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when PUT request fails", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
        credentials: "include",
      });
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error when DELETE request fails", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
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
      (global.fetch as jest.Mock).mockRejectedValueOnce(
        new Error("Network error")
      );

      await expect(api.get("/test")).rejects.toThrow("Network error");
    });

    it("should handle token retrieval errors", async () => {
      const tokenError = new Error("Token error");
      (getAccessToken as jest.Mock).mockRejectedValueOnce(tokenError);

      await expect(api.get("/test")).rejects.toThrow("Token error");
    });
  });
});
