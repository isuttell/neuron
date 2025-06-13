import { vi } from "vitest";

/**
 * Creates mock functions for react-router-dom
 * @returns Object containing mockNavigate and other router mocks
 */
export const createRouterMocks = () => {
  const mockNavigate = vi.fn();
  const mockLocation = {
    pathname: "/",
    search: "",
    hash: "",
    state: null,
    key: "default",
  };
  const mockParams = {};

  return {
    mockNavigate,
    mockLocation,
    mockParams,
  };
};

/**
 * Creates a complete mock for react-router-dom module
 * @returns Mock module with all necessary exports
 */
export const createReactRouterDomMock = async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  const { mockNavigate, mockLocation, mockParams } = createRouterMocks();

  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
    useParams: () => mockParams,
  };
};
