import { getCurrentBuildHash, simpleHash } from '../buildHash';

// Mock DOM for testing
const mockScriptElement = (src: string) => {
  const element = document.createElement('script');
  element.src = src;
  return element;
};

describe('buildHash utilities', () => {
  beforeEach(() => {
    // Clear the document head before each test
    document.head.innerHTML = '';
  });

  describe('getCurrentBuildHash', () => {
    it('extracts hash from main index script with hash pattern', () => {
      const script = mockScriptElement('/assets/index-B6LUCei6.js');
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('B6LUCei6');
    });

    it('extracts hash from any script with hash pattern', () => {
      const script = mockScriptElement('/assets/vendor-A1B2C3D4.js');
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('A1B2C3D4');
    });

    it('prefers index script over other scripts', () => {
      const vendorScript = mockScriptElement('/assets/vendor-VENDOR99.js');
      const indexScript = mockScriptElement('/assets/index-INDEX88.js');

      document.head.appendChild(vendorScript);
      document.head.appendChild(indexScript);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('INDEX88');
    });

    it('returns "dev" when no hashed assets found', () => {
      const script = mockScriptElement('/main.js');
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('dev');
    });

    it('returns "dev" when no scripts found', () => {
      const hash = getCurrentBuildHash();
      expect(hash).toBe('dev');
    });

    it('handles scripts without src attribute', () => {
      const script = document.createElement('script');
      script.textContent = 'console.log("inline");';
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('dev');
    });

    it('handles malformed asset paths gracefully', () => {
      const script = mockScriptElement('/assets/');
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('dev');
    });

    it('extracts hash from complex filename patterns', () => {
      const script = mockScriptElement('/assets/main-component-X9Y8Z7W6.js');
      document.head.appendChild(script);

      const hash = getCurrentBuildHash();
      expect(hash).toBe('X9Y8Z7W6');
    });
  });

  describe('simpleHash', () => {
    it('generates consistent hash for same string', () => {
      const str = 'test string';
      const hash1 = simpleHash(str);
      const hash2 = simpleHash(str);

      expect(hash1).toBe(hash2);
    });

    it('generates different hashes for different strings', () => {
      const hash1 = simpleHash('string1');
      const hash2 = simpleHash('string2');

      expect(hash1).not.toBe(hash2);
    });

    it('handles empty string', () => {
      const hash = simpleHash('');
      expect(typeof hash).toBe('string');
      expect(hash.length).toBeGreaterThan(0);
    });

    it('generates valid base36 string', () => {
      const hash = simpleHash('test');
      expect(hash).toMatch(/^[0-9a-z]+$/);
    });
  });
});
