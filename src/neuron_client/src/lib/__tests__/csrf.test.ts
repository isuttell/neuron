import { vi } from 'vitest';
import { setCSRFToken, clearCSRFToken, addCSRFToFormData } from '../csrf';

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
});

describe('CSRF Token Management', () => {
  const testToken = 'test-csrf-token';

  beforeEach(() => {
    vi.clearAllMocks();
    clearCSRFToken();
  });

  describe('addCSRFToFormData', () => {
    it('should add CSRF token to FormData when token is available', () => {
      // Set up CSRF token
      setCSRFToken(testToken);
      mockSessionStorage.getItem.mockReturnValue(testToken);

      const formData = new FormData();
      formData.append('field1', 'value1');

      const result = addCSRFToFormData(formData);

      expect(result.get('csrf_token')).toBe(testToken);
      expect(result.get('field1')).toBe('value1');
    });

    it('should not add CSRF token when no token is available', () => {
      // No CSRF token set
      clearCSRFToken();
      mockSessionStorage.getItem.mockReturnValue(null);

      const formData = new FormData();
      formData.append('field1', 'value1');

      const result = addCSRFToFormData(formData);

      expect(result.get('csrf_token')).toBeNull();
      expect(result.get('field1')).toBe('value1');
    });

    it('should replace existing CSRF token in FormData', () => {
      const oldToken = 'old-csrf-token';
      const newToken = 'new-csrf-token';

      // Set up new CSRF token
      setCSRFToken(newToken);
      mockSessionStorage.getItem.mockReturnValue(newToken);

      const formData = new FormData();
      formData.append('field1', 'value1');
      formData.append('csrf_token', oldToken); // Add old token first

      const result = addCSRFToFormData(formData);

      // Should have the new token, not the old one
      expect(result.get('csrf_token')).toBe(newToken);
      expect(result.get('field1')).toBe('value1');

      // Verify only one csrf_token entry exists
      const tokens = result.getAll('csrf_token');
      expect(tokens).toHaveLength(1);
      expect(tokens[0]).toBe(newToken);
    });

    it('should handle FormData with multiple values for same field', () => {
      setCSRFToken(testToken);
      mockSessionStorage.getItem.mockReturnValue(testToken);

      const formData = new FormData();
      formData.append('field1', 'value1');
      formData.append('field1', 'value2'); // Multiple values
      formData.append('csrf_token', 'old-token');

      const result = addCSRFToFormData(formData);

      expect(result.get('csrf_token')).toBe(testToken);
      expect(result.getAll('field1')).toEqual(['value1', 'value2']);
    });

    it('should preserve all other FormData entries when replacing token', () => {
      const oldToken = 'old-token';
      const newToken = 'new-token';

      setCSRFToken(newToken);
      mockSessionStorage.getItem.mockReturnValue(newToken);

      const formData = new FormData();
      formData.append('name', 'John');
      formData.append('email', 'john@example.com');
      formData.append('csrf_token', oldToken);
      formData.append('age', '30');

      const result = addCSRFToFormData(formData);

      expect(result.get('csrf_token')).toBe(newToken);
      expect(result.get('name')).toBe('John');
      expect(result.get('email')).toBe('john@example.com');
      expect(result.get('age')).toBe('30');
    });

    it('should return the same FormData instance (modified in place)', () => {
      setCSRFToken(testToken);
      mockSessionStorage.getItem.mockReturnValue(testToken);

      const formData = new FormData();
      formData.append('field1', 'value1');

      const result = addCSRFToFormData(formData);

      // Should return the same instance
      expect(result).toBe(formData);
      expect(formData.get('csrf_token')).toBe(testToken);
    });
  });
});
