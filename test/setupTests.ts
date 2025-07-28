import "@testing-library/jest-dom/vitest";
import { vi, afterEach } from "vitest";

// Mock fetch globally
global.fetch = vi.fn();

// Mock HTMLMediaElement methods to avoid jsdom warnings
global.HTMLMediaElement.prototype.pause = vi.fn();
global.HTMLMediaElement.prototype.play = vi.fn();

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();

// Mock anchor element click to prevent navigation errors
const originalCreateElement = document.createElement.bind(document);
document.createElement = vi.fn((tagName: string) => {
  const element = originalCreateElement(tagName);
  if (tagName === 'a') {
    element.click = vi.fn();
  }
  return element;
}) as unknown as typeof document.createElement;

// Reset all mocks after each test
afterEach(() => {
  vi.clearAllMocks();
});
