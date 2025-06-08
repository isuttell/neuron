import { User } from "@auth0/auth0-react";
import {
  PERMISSIONS,
  ROLES,
  getUserPermissions,
  getUserRoles,
  hasPermission,
  hasRole,
  isAdmin,
  canAccessPrompts,
  canAccessProviders,
} from "../auth";

describe("auth utilities", () => {
  describe("constants", () => {
    it("exports permission constants", () => {
      expect(PERMISSIONS.ADMIN_PROMPTS).toBe("admin-prompts");
      expect(PERMISSIONS.ADMIN_PROVIDERS).toBe("admin-providers");
      expect(PERMISSIONS.ADMIN).toBe("admin");
    });

    it("exports role constants", () => {
      expect(ROLES.ADMIN).toBe("admin");
    });
  });

  describe("getUserPermissions", () => {
    it("returns permissions array when user has permissions", () => {
      const user = {
        permissions: ["admin-prompts", "admin-providers"],
      } as User;

      expect(getUserPermissions(user)).toEqual(["admin-prompts", "admin-providers"]);
    });

    it("returns empty array when user has no permissions", () => {
      const user = {} as User;
      expect(getUserPermissions(user)).toEqual([]);
    });

    it("returns empty array when user is undefined", () => {
      expect(getUserPermissions(undefined)).toEqual([]);
    });
  });

  describe("getUserRoles", () => {
    it("returns roles array when user has roles", () => {
      const user = {
        "neuron/roles": ["admin", "user"],
      } as User;

      expect(getUserRoles(user)).toEqual(["admin", "user"]);
    });

    it("returns empty array when user has no roles", () => {
      const user = {} as User;
      expect(getUserRoles(user)).toEqual([]);
    });

    it("returns empty array when user is undefined", () => {
      expect(getUserRoles(undefined)).toEqual([]);
    });
  });

  describe("hasPermission", () => {
    it("returns true when user has the permission", () => {
      const user = {
        permissions: ["admin-prompts", "admin-providers"],
      } as User;

      expect(hasPermission(user, "admin-prompts")).toBe(true);
      expect(hasPermission(user, "admin-providers")).toBe(true);
    });

    it("returns false when user does not have the permission", () => {
      const user = {
        permissions: ["admin-prompts"],
      } as User;

      expect(hasPermission(user, "admin-providers")).toBe(false);
      expect(hasPermission(user, "non-existent")).toBe(false);
    });

    it("returns false when user has no permissions", () => {
      const user = {} as User;
      expect(hasPermission(user, "admin-prompts")).toBe(false);
    });

    it("returns false when user is undefined", () => {
      expect(hasPermission(undefined, "admin-prompts")).toBe(false);
    });
  });

  describe("hasRole", () => {
    it("returns true when user has the role", () => {
      const user = {
        "neuron/roles": ["admin", "user"],
      } as User;

      expect(hasRole(user, "admin")).toBe(true);
      expect(hasRole(user, "user")).toBe(true);
    });

    it("returns false when user does not have the role", () => {
      const user = {
        "neuron/roles": ["user"],
      } as User;

      expect(hasRole(user, "admin")).toBe(false);
      expect(hasRole(user, "non-existent")).toBe(false);
    });

    it("returns false when user has no roles", () => {
      const user = {} as User;
      expect(hasRole(user, "admin")).toBe(false);
    });

    it("returns false when user is undefined", () => {
      expect(hasRole(undefined, "admin")).toBe(false);
    });
  });

  describe("isAdmin", () => {
    it("returns true when user has admin role", () => {
      const user = {
        "neuron/roles": ["admin", "user"],
      } as User;

      expect(isAdmin(user)).toBe(true);
    });

    it("returns false when user does not have admin role", () => {
      const user = {
        "neuron/roles": ["user"],
      } as User;

      expect(isAdmin(user)).toBe(false);
    });

    it("returns false when user has no roles", () => {
      const user = {} as User;
      expect(isAdmin(user)).toBe(false);
    });

    it("returns false when user is undefined", () => {
      expect(isAdmin(undefined)).toBe(false);
    });
  });

  describe("canAccessPrompts", () => {
    it("returns true when user has admin-prompts permission", () => {
      const user = {
        permissions: ["admin-prompts", "other-permission"],
      } as User;

      expect(canAccessPrompts(user)).toBe(true);
    });

    it("returns false when user does not have admin-prompts permission", () => {
      const user = {
        permissions: ["admin-providers"],
      } as User;

      expect(canAccessPrompts(user)).toBe(false);
    });

    it("returns false when user has no permissions", () => {
      const user = {} as User;
      expect(canAccessPrompts(user)).toBe(false);
    });

    it("returns false when user is undefined", () => {
      expect(canAccessPrompts(undefined)).toBe(false);
    });
  });

  describe("canAccessProviders", () => {
    it("returns true when user has admin-providers permission", () => {
      const user = {
        permissions: ["admin-providers", "other-permission"],
      } as User;

      expect(canAccessProviders(user)).toBe(true);
    });

    it("returns false when user does not have admin-providers permission", () => {
      const user = {
        permissions: ["admin-prompts"],
      } as User;

      expect(canAccessProviders(user)).toBe(false);
    });

    it("returns false when user has no permissions", () => {
      const user = {} as User;
      expect(canAccessProviders(user)).toBe(false);
    });

    it("returns false when user is undefined", () => {
      expect(canAccessProviders(undefined)).toBe(false);
    });
  });
});
