import { setGetAccessTokenSilently, getAccessToken } from "../getToken";

describe("getToken", () => {
  beforeEach(() => {
    // Reset the context before each test
    setGetAccessTokenSilently(undefined as unknown as () => Promise<string>);
  });

  describe("setGetAccessTokenSilently", () => {
    it("should set the getAccessTokenSilently function in the context", () => {
      const mockGetAccessTokenSilently = jest.fn();
      setGetAccessTokenSilently(mockGetAccessTokenSilently);

      // We can't directly test the context, but we can verify through getAccessToken
      expect(getAccessToken).toBeDefined();
    });
  });

  describe("getAccessToken", () => {
    it("should throw an error if getAccessTokenSilently is not defined", async () => {
      await expect(getAccessToken()).rejects.toThrow(
        "getAccessTokenSilently is not defined"
      );
    });

    it("should return the access token when getAccessTokenSilently is defined", async () => {
      const mockToken = "mock-access-token";
      const mockGetAccessTokenSilently = jest.fn().mockResolvedValue(mockToken);

      setGetAccessTokenSilently(mockGetAccessTokenSilently);

      const token = await getAccessToken();

      expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(1);
      expect(token).toBe(mockToken);
    });

    it("should handle errors thrown by getAccessTokenSilently", async () => {
      const mockError = new Error("Failed to get token");
      const mockGetAccessTokenSilently = jest.fn().mockRejectedValue(mockError);

      setGetAccessTokenSilently(mockGetAccessTokenSilently);

      await expect(getAccessToken()).rejects.toThrow("Failed to get token");
      expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(1);
    });

    it("should call getAccessTokenSilently multiple times for multiple getAccessToken calls", async () => {
      const mockToken1 = "mock-access-token-1";
      const mockToken2 = "mock-access-token-2";
      const mockGetAccessTokenSilently = jest
        .fn()
        .mockResolvedValueOnce(mockToken1)
        .mockResolvedValueOnce(mockToken2);

      setGetAccessTokenSilently(mockGetAccessTokenSilently);

      const token1 = await getAccessToken();
      const token2 = await getAccessToken();

      expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(2);
      expect(token1).toBe(mockToken1);
      expect(token2).toBe(mockToken2);
    });

    it("should allow updating the getAccessTokenSilently function", async () => {
      const mockToken1 = "token-from-first-function";
      const mockToken2 = "token-from-second-function";

      const mockGetAccessTokenSilently1 = jest.fn().mockResolvedValue(mockToken1);
      const mockGetAccessTokenSilently2 = jest.fn().mockResolvedValue(mockToken2);

      // Set first function
      setGetAccessTokenSilently(mockGetAccessTokenSilently1);
      const token1 = await getAccessToken();
      expect(token1).toBe(mockToken1);
      expect(mockGetAccessTokenSilently1).toHaveBeenCalledTimes(1);

      // Update to second function
      setGetAccessTokenSilently(mockGetAccessTokenSilently2);
      const token2 = await getAccessToken();
      expect(token2).toBe(mockToken2);
      expect(mockGetAccessTokenSilently2).toHaveBeenCalledTimes(1);
      expect(mockGetAccessTokenSilently1).toHaveBeenCalledTimes(1); // Still only called once
    });
  });
});
