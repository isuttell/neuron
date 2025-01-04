type GetAccessTokenSilently = () => Promise<string>;

/**
 * Store the getAccessTokenSilently function in a global context
 * so that it can be used in other actions
 */
const context = {
  getAccessTokenSilently: undefined,
} as { getAccessTokenSilently: GetAccessTokenSilently | undefined };

/**
 * Set the getAccessTokenSilently function in the global context
 * so that it can be used in other actions
 */
export const setGetAccessTokenSilently = (
  getAccessTokenSilently: GetAccessTokenSilently
) => {
  context.getAccessTokenSilently = getAccessTokenSilently;
};

/**
 * Get the access token from the global context
 */
export const getAccessToken = async () => {
  if (!context.getAccessTokenSilently) {
    throw new Error("getAccessTokenSilently is not defined");
  }
  const accessToken = await context.getAccessTokenSilently();
  return accessToken;
};
