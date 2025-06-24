import React from 'react';
import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import type { User } from '@auth0/auth0-react';
import { usePersonalityPermissions } from '../usePersonalityPermissions';
import personalitiesReducer from '../../slices/personalitiesSlice';
import type { Personality } from '../../types/personality';

// Mock Auth0
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: vi.fn(),
}));

// Mock the isAdmin function
vi.mock('../../lib/auth', () => ({
  isAdmin: vi.fn(),
}));

import { useAuth0 } from '@auth0/auth0-react';
import { isAdmin } from '../../lib/auth';

const mockUseAuth0 = vi.mocked(useAuth0);
const mockIsAdmin = vi.mocked(isAdmin);

describe('usePersonalityPermissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAdmin.mockReturnValue(false);
  });

  const mockPersonality: Personality = {
    id: 'personality-123',
    name: 'Test Personality',
    description: 'Test description',
    context: 'Test context',
    memory: 'Test memory',
    tool_set: 'default',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  const mockPersonalityUsers = [
    {
      id: 'user-123',
      email: 'admin@test.com',
      nickname: 'admin',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      role: 'admin',
    },
    {
      id: 'user-456',
      email: 'user@test.com',
      nickname: 'user',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      role: 'user',
    },
  ];

  const createTestStore = (personalityId?: string, personalities: Personality[] = [], personalityUsers: Record<string, unknown> = {}) => {
    return configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
      preloadedState: {
        personalities: {
          personalities,
          personalityUsers,
          activePersonalityId: undefined,
          loading: false,
          error: null,
          hasInitiallyFetched: true,
        },
      },
    });
  };

  const renderHookWithProvider = (personalityId?: string, storeOptions: Record<string, unknown> = {}) => {
    const store = createTestStore(personalityId, [mockPersonality], {
      'personality-123': mockPersonalityUsers,
      ...storeOptions,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );

    return renderHook(() => usePersonalityPermissions(personalityId), { wrapper });
  };

  describe('with system admin user', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'admin-123',
          'neuron/roles': ['admin'],
          permissions: ['admin'],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
      mockIsAdmin.mockReturnValue(true);
    });

    it('returns true for all permissions regardless of personality role', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.canManage).toBe(true);
      expect(result.current.canManageUsers).toBe(true);
      expect(result.current.canDelete).toBe(true);
      expect(result.current.canUse).toBe(true);
      expect(result.current.hasAnyActions).toBe(true);
      expect(result.current.shouldShowComponent).toBe(true);
    });

    it('returns personality with converted users', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.personality).toBeDefined();
      expect(result.current.personality?.id).toBe('personality-123');
      expect(result.current.personality?.personality_users).toHaveLength(2);
      expect(result.current.personality?.personality_users?.[0]).toEqual({
        user_id: 'user-123',
        personality_id: 'personality-123',
        role: 'admin',
      });
    });
  });

  describe('with personality admin user', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns true for admin permissions', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.canManage).toBe(true);
      expect(result.current.canManageUsers).toBe(true);
      expect(result.current.canDelete).toBe(true);
      expect(result.current.canUse).toBe(true);
      expect(result.current.hasAnyActions).toBe(true);
      expect(result.current.shouldShowComponent).toBe(true);
      expect(result.current.userRole).toBe('admin');
      expect(result.current.isAdmin).toBe(true);
      expect(result.current.hasAccess).toBe(true);
    });
  });

  describe('with personality user (non-admin)', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-456',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns limited permissions for user role', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.canManage).toBe(false);
      expect(result.current.canManageUsers).toBe(false);
      expect(result.current.canDelete).toBe(false);
      expect(result.current.canUse).toBe(true);
      expect(result.current.hasAnyActions).toBe(false); // No admin actions
      expect(result.current.shouldShowComponent).toBe(false);
      expect(result.current.userRole).toBe('user');
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.hasAccess).toBe(true);
    });
  });

  describe('with user having no personality access', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'unknown-user',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns false for all permissions', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.canManage).toBe(false);
      expect(result.current.canManageUsers).toBe(false);
      expect(result.current.canDelete).toBe(false);
      expect(result.current.canUse).toBe(false);
      expect(result.current.hasAnyActions).toBe(false);
      expect(result.current.shouldShowComponent).toBe(false);
      expect(result.current.userRole).toBe(null);
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.hasAccess).toBe(false);
    });
  });

  describe('with undefined user', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: undefined,
        isAuthenticated: false,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns false for all permissions', () => {
      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.canManage).toBe(false);
      expect(result.current.canManageUsers).toBe(false);
      expect(result.current.canDelete).toBe(false);
      expect(result.current.canUse).toBe(false);
      expect(result.current.hasAnyActions).toBe(false);
      expect(result.current.shouldShowComponent).toBe(false);
      expect(result.current.userRole).toBe(null);
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.hasAccess).toBe(false);
    });
  });

  describe('with undefined personalityId', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns false for all permissions when personalityId is undefined', () => {
      const { result } = renderHookWithProvider(undefined);

      expect(result.current.canManage).toBe(false);
      expect(result.current.canManageUsers).toBe(false);
      expect(result.current.canDelete).toBe(false);
      expect(result.current.canUse).toBe(false);
      expect(result.current.hasAnyActions).toBe(false);
      expect(result.current.shouldShowComponent).toBe(false);
      expect(result.current.personality).toBe(undefined);
    });
  });

  describe('with missing personality in store', () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);
    });

    it('returns false for all permissions when personality not found', () => {
      const store = createTestStore('nonexistent-personality', [], {});
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      const { result } = renderHook(() => usePersonalityPermissions('nonexistent-personality'), { wrapper });

      expect(result.current.canManage).toBe(false);
      expect(result.current.canManageUsers).toBe(false);
      expect(result.current.canDelete).toBe(false);
      expect(result.current.canUse).toBe(false);
      expect(result.current.hasAnyActions).toBe(false);
      expect(result.current.shouldShowComponent).toBe(false);
      expect(result.current.personality).toBe(undefined);
    });
  });

  describe('memoization', () => {
    it('returns same object reference when dependencies have not changed', () => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);

      const { result, rerender } = renderHookWithProvider('personality-123');
      const firstResult = result.current;

      rerender();
      const secondResult = result.current;

      expect(firstResult).toBe(secondResult);
    });

    it('returns new object reference when user changes', () => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);

      const { result, rerender } = renderHookWithProvider('personality-123');
      const firstResult = result.current;

      // Change user
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-456',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);

      rerender();
      const secondResult = result.current;

      expect(firstResult).not.toBe(secondResult);
    });
  });

  describe('conversion from UserWithRole to PersonalityUser', () => {
    it('correctly converts Redux UserWithRole format to PersonalityUser format', () => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);

      const { result } = renderHookWithProvider('personality-123');

      expect(result.current.personality?.personality_users).toEqual([
        {
          user_id: 'user-123',
          personality_id: 'personality-123',
          role: 'admin',
        },
        {
          user_id: 'user-456',
          personality_id: 'personality-123',
          role: 'user',
        },
      ]);
    });

    it('handles empty personality users array', () => {
      mockUseAuth0.mockReturnValue({
        user: {
          sub: 'user-123',
          'neuron/roles': ['user'],
          permissions: [],
        } as User,
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth0>);

      const { result } = renderHookWithProvider('personality-123', { 'personality-123': [] });

      expect(result.current.personality?.personality_users).toEqual([]);
      expect(result.current.canManage).toBe(false);
      expect(result.current.canUse).toBe(false);
    });
  });
});
