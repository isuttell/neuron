/**
 * Utility functions for extracting and working with build hashes
 */

/**
 * Extract the asset hash from the current page's main script src
 * The hash is embedded in the filename like: index-B6LUCei6.js
 */
export function getCurrentBuildHash(): string | null {
  try {
    // Find the main script tag with the hashed filename
    const scriptTags = document.querySelectorAll('script[src*="/assets/index-"]');

    for (const script of scriptTags) {
      const src = script.getAttribute('src');
      if (src) {
        // Extract hash from filename like /assets/index-B6LUCei6.js
        const match = src.match(/\/assets\/index-([a-zA-Z0-9]+)\.js$/);
        if (match) {
          return match[1];
        }
      }
    }

    // Fallback: try to extract from any script with hash pattern in assets directory
    const allScripts = document.querySelectorAll('script[src*="/assets/"]');
    for (const script of allScripts) {
      const src = script.getAttribute('src');
      if (src) {
        // Match any file with pattern: filename-hash.js or complex-filename-hash.js
        const match = src.match(/\/assets\/[\w-]+-([a-zA-Z0-9]+)\.js$/);
        if (match) {
          return match[1];
        }
      }
    }

    // Development fallback: if no hashed assets found, return 'dev'
    return 'dev';
  } catch (error) {
    console.warn('Failed to extract build hash:', error);
    return 'dev';
  }
}

/**
 * Generate a simple hash from a string (for fallback purposes)
 */
export function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}
