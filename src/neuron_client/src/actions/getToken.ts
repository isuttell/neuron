import { handleAuth0Error } from "@/lib/authErrorHandler";

type GetAccessTokenSilently = () => Promise<string>;
type LoginWithRedirect = (options?: { appState?: { returnTo?: string } }) => Promise<void>;

/**
 * Store the Auth0 functions in a global context
 * so that they can be used in other actions
 */
const context = {
  getAccessTokenSilently: undefined,
  loginWithRedirect: undefined,
} as {
  getAccessTokenSilently: GetAccessTokenSilently | undefined;
  loginWithRedirect: LoginWithRedirect | undefined;
};

/**
 * Set the Auth0 functions in the global context
 * so that they can be used in other actions
 */
export const setAuth0Functions = (
  getAccessTokenSilently: GetAccessTokenSilently,
  loginWithRedirect: LoginWithRedirect
) => {
  context.getAccessTokenSilently = getAccessTokenSilently;
  context.loginWithRedirect = loginWithRedirect;
};

/**
 * Legacy function for backward compatibility
 * @deprecated Use setAuth0Functions instead
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

  try {
    const accessToken = await context.getAccessTokenSilently();
    return accessToken;
  } catch (error) {
    // Handle Auth0 SDK errors properly using loginWithRedirect
    if (context.loginWithRedirect) {
      handleAuth0Error(error, context.loginWithRedirect);
    } else {
      console.warn('loginWithRedirect not available, cannot handle Auth0 error properly:', error);
    }
    throw error;
  }
};
