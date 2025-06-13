import { vi } from 'vitest';
import { renderHook } from "@testing-library/react";
import { User, Auth0ContextInterface } from "@auth0/auth0-react";
import { usePermissions } from "../usePermissions";
import * as auth0React from "@auth0/auth0-react";

// Mock Auth0 hook
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

describe("usePermissions", () => {
  const mockUseAuth0 = vi.spyOn(auth0React, "useAuth0");

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns permission data and utility functions", () => {
    const mockUser = {
      permissions: ["admin-prompts", "admin-providers"],
      "neuron/roles": ["admin"],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser,
    } as Auth0ContextInterface<User>);

    const { result } = renderHook(() => usePermissions());

    expect(result.current.permissions).toEqual(["admin-prompts", "admin-providers"]);
    expect(result.current.roles).toEqual(["admin"]);
    expect(result.current.isAdmin).toBe(true);
    expect(result.current.canAccessPrompts).toBe(true);
    expect(result.current.canAccessProviders).toBe(true);
    expect(typeof result.current.hasPermission).toBe("function");
    expect(typeof result.current.hasRole).toBe("function");
    expect(result.current.PERMISSIONS).toBeDefined();
    expect(result.current.ROLES).toBeDefined();
  });

  it("returns correct permission flags when user has specific permissions", () => {
    const mockUser = {
      permissions: ["admin-prompts"],
      "neuron/roles": [],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser,
    } as Auth0ContextInterface<User>);

    const { result } = renderHook(() => usePermissions());

    expect(result.current.canAccessPrompts).toBe(true);
    expect(result.current.canAccessProviders).toBe(false);
    expect(result.current.isAdmin).toBe(false);
  });

  it("returns false for all permissions when user has none", () => {
    const mockUser = {
      permissions: [],
      "neuron/roles": [],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser,
    } as Auth0ContextInterface<User>);

    const { result } = renderHook(() => usePermissions());

    expect(result.current.canAccessPrompts).toBe(false);
    expect(result.current.canAccessProviders).toBe(false);
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.permissions).toEqual([]);
    expect(result.current.roles).toEqual([]);
  });

  it("handles undefined user gracefully", () => {
    mockUseAuth0.mockReturnValue({
      user: undefined,
    } as Auth0ContextInterface<User>);

    const { result } = renderHook(() => usePermissions());

    expect(result.current.canAccessPrompts).toBe(false);
    expect(result.current.canAccessProviders).toBe(false);
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.permissions).toEqual([]);
    expect(result.current.roles).toEqual([]);
  });

  it("utility functions work correctly", () => {
    const mockUser = {
      permissions: ["admin-prompts", "custom-permission"],
      "neuron/roles": ["admin", "custom-role"],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser,
    } as Auth0ContextInterface<User>);

    const { result } = renderHook(() => usePermissions());

    expect(result.current.hasPermission("admin-prompts")).toBe(true);
    expect(result.current.hasPermission("admin-providers")).toBe(false);
    expect(result.current.hasPermission("custom-permission")).toBe(true);

    expect(result.current.hasRole("admin")).toBe(true);
    expect(result.current.hasRole("user")).toBe(false);
    expect(result.current.hasRole("custom-role")).toBe(true);
  });

  it("memoizes the result correctly", () => {
    const mockUser = {
      permissions: ["admin-prompts"],
      "neuron/roles": ["admin"],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser,
    } as Auth0ContextInterface<User>);

    const { result, rerender } = renderHook(() => usePermissions());
    const firstResult = result.current;

    // Rerender with same user
    rerender();
    const secondResult = result.current;

    // Should be the same object due to memoization
    expect(firstResult).toBe(secondResult);
  });

  it("updates when user changes", () => {
    const mockUser1 = {
      permissions: ["admin-prompts"],
      "neuron/roles": ["admin"],
    } as User;

    const mockUser2 = {
      permissions: ["admin-providers"],
      "neuron/roles": ["user"],
    } as User;

    mockUseAuth0.mockReturnValue({
      user: mockUser1,
    } as Auth0ContextInterface<User>);

    const { result, rerender } = renderHook(() => usePermissions());

    expect(result.current.canAccessPrompts).toBe(true);
    expect(result.current.canAccessProviders).toBe(false);
    expect(result.current.isAdmin).toBe(true);

    // Change user
    mockUseAuth0.mockReturnValue({
      user: mockUser2,
    } as Auth0ContextInterface<User>);

    rerender();

    expect(result.current.canAccessPrompts).toBe(false);
    expect(result.current.canAccessProviders).toBe(true);
    expect(result.current.isAdmin).toBe(false);
  });
});
