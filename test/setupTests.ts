import "@testing-library/jest-dom/vitest";
import { vi, afterEach } from "vitest";

// Mock fetch globally
global.fetch = vi.fn();

// Mock HTMLMediaElement methods to avoid jsdom warnings
global.HTMLMediaElement.prototype.pause = vi.fn();
global.HTMLMediaElement.prototype.play = vi.fn();

// Reset all mocks after each test
afterEach(() => {
  vi.clearAllMocks();
});
