import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { User } from '@auth0/auth0-react';
import type { Personality, PersonalityUser } from '../../types/personality';
import {
  isPersonalityAdmin,
  canManagePersonality,
  canUsePersonality,
  canManagePersonalityUsers,
  canDeletePersonality,
  hasPersonalityAccess,
  hasAnyPersonalityActions,
  getPersonalityUserRole,
} from '../personalityPermissions';

// Mock the isAdmin function
vi.mock('../auth', () => ({
  isAdmin: vi.fn(),
}));

import { isAdmin } from '../auth';
const mockIsAdmin = vi.mocked(isAdmin);

describe('personalityPermissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test data
  const mockUser: User = {
    sub: 'user-123',
    'neuron/roles': ['user'],
    permissions: [],
  };

  const mockSystemAdmin: User = {
    sub: 'admin-123',
    'neuron/roles': ['admin'],
    permissions: ['admin'],
  };

  const mockPersonalityUsers: PersonalityUser[] = [
    {
      user_id: 'user-123',
      personality_id: 'personality-456',
      role: 'admin',
    },
    {
      user_id: 'user-789',
      personality_id: 'personality-456',
      role: 'user',
    },
  ];

  const mockPersonality: Personality = {
    id: 'personality-456',
    name: 'Test Personality',
    description: 'Test description',
    context: 'Test context',
    memory: 'Test memory',
    tool_set: 'default',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    personality_users: mockPersonalityUsers,
  };

  const mockPersonalityNoUsers: Personality = {
    ...mockPersonality,
    personality_users: [],
  };

  describe('isPersonalityAdmin', () => {
    it('returns true when user has admin role for personality', () => {
      const result = isPersonalityAdmin(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false when user has user role for personality', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = isPersonalityAdmin(userWithUserRole, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when user is not in personality_users', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = isPersonalityAdmin(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when personality has no users', () => {
      const result = isPersonalityAdmin(mockUser, mockPersonalityNoUsers);
      expect(result).toBe(false);
    });

    it('returns false when user is undefined', () => {
      const result = isPersonalityAdmin(undefined, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when personality is undefined', () => {
      const result = isPersonalityAdmin(mockUser, undefined);
      expect(result).toBe(false);
    });

    it('returns false when personality_users is undefined', () => {
      const personalityWithoutUsers: Personality = {
        ...mockPersonality,
        personality_users: undefined,
      };
      const result = isPersonalityAdmin(mockUser, personalityWithoutUsers);
      expect(result).toBe(false);
    });
  });

  describe('canManagePersonality', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin regardless of personality role', () => {
      mockIsAdmin.mockReturnValue(true);
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = canManagePersonality(unknownUser, mockPersonality);
      expect(result).toBe(true);
      expect(mockIsAdmin).toHaveBeenCalledWith(unknownUser);
    });

    it('returns true for personality admin', () => {
      const result = canManagePersonality(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for personality user (non-admin)', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = canManagePersonality(userWithUserRole, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = canManagePersonality(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when user is undefined', () => {
      const result = canManagePersonality(undefined, mockPersonality);
      expect(result).toBe(false);
    });
  });

  describe('canUsePersonality', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin', () => {
      mockIsAdmin.mockReturnValue(true);
      const result = canUsePersonality(mockSystemAdmin, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality admin', () => {
      const result = canUsePersonality(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality user', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = canUsePersonality(userWithUserRole, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = canUsePersonality(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when user is undefined', () => {
      const result = canUsePersonality(undefined, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when personality is undefined', () => {
      const result = canUsePersonality(mockUser, undefined);
      expect(result).toBe(false);
    });

    it('returns false when personality_users is undefined', () => {
      const personalityWithoutUsers: Personality = {
        ...mockPersonality,
        personality_users: undefined,
      };
      const result = canUsePersonality(mockUser, personalityWithoutUsers);
      expect(result).toBe(false);
    });
  });

  describe('canManagePersonalityUsers', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin', () => {
      mockIsAdmin.mockReturnValue(true);
      const result = canManagePersonalityUsers(mockSystemAdmin, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality admin', () => {
      const result = canManagePersonalityUsers(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for personality user (non-admin)', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = canManagePersonalityUsers(userWithUserRole, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = canManagePersonalityUsers(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });
  });

  describe('canDeletePersonality', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin', () => {
      mockIsAdmin.mockReturnValue(true);
      const result = canDeletePersonality(mockSystemAdmin, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality admin', () => {
      const result = canDeletePersonality(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for personality user (non-admin)', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = canDeletePersonality(userWithUserRole, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = canDeletePersonality(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });
  });

  describe('hasPersonalityAccess', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin', () => {
      mockIsAdmin.mockReturnValue(true);
      const result = hasPersonalityAccess(mockSystemAdmin, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality admin', () => {
      const result = hasPersonalityAccess(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality user', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = hasPersonalityAccess(userWithUserRole, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = hasPersonalityAccess(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when user is undefined', () => {
      const result = hasPersonalityAccess(undefined, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when personality is undefined', () => {
      const result = hasPersonalityAccess(mockUser, undefined);
      expect(result).toBe(false);
    });
  });

  describe('hasAnyPersonalityActions', () => {
    beforeEach(() => {
      mockIsAdmin.mockReturnValue(false);
    });

    it('returns true for system admin', () => {
      mockIsAdmin.mockReturnValue(true);
      const result = hasAnyPersonalityActions(mockSystemAdmin, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns true for personality admin', () => {
      const result = hasAnyPersonalityActions(mockUser, mockPersonality);
      expect(result).toBe(true);
    });

    it('returns false for personality user (non-admin)', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = hasAnyPersonalityActions(userWithUserRole, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = hasAnyPersonalityActions(unknownUser, mockPersonality);
      expect(result).toBe(false);
    });

    it('returns false when user is undefined', () => {
      const result = hasAnyPersonalityActions(undefined, mockPersonality);
      expect(result).toBe(false);
    });
  });

  describe('getPersonalityUserRole', () => {
    it('returns admin role for personality admin', () => {
      const result = getPersonalityUserRole(mockUser, mockPersonality);
      expect(result).toBe('admin');
    });

    it('returns user role for personality user', () => {
      const userWithUserRole: User = {
        ...mockUser,
        sub: 'user-789',
      };
      const result = getPersonalityUserRole(userWithUserRole, mockPersonality);
      expect(result).toBe('user');
    });

    it('returns null for user with no personality access', () => {
      const unknownUser: User = {
        ...mockUser,
        sub: 'unknown-user',
      };
      const result = getPersonalityUserRole(unknownUser, mockPersonality);
      expect(result).toBe(null);
    });

    it('returns null when user is undefined', () => {
      const result = getPersonalityUserRole(undefined, mockPersonality);
      expect(result).toBe(null);
    });

    it('returns null when personality is undefined', () => {
      const result = getPersonalityUserRole(mockUser, undefined);
      expect(result).toBe(null);
    });

    it('returns null when personality_users is undefined', () => {
      const personalityWithoutUsers: Personality = {
        ...mockPersonality,
        personality_users: undefined,
      };
      const result = getPersonalityUserRole(mockUser, personalityWithoutUsers);
      expect(result).toBe(null);
    });
  });
});
