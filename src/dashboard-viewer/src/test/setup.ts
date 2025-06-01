import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Store instances for testing
const mockWebSocketInstances: MockWebSocket[] = []

// Mock WebSocket for testing
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(public url: string) {
    mockWebSocketInstances.push(this)

    // Simulate connection after a tick
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  send(_data: string) {
    // Mock implementation
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }

  static resetInstances() {
    mockWebSocketInstances.length = 0
  }

  static getInstances() {
    return mockWebSocketInstances
  }
}

// Add mock property to access instances
(MockWebSocket as any).mock = {
  instances: mockWebSocketInstances
}

global.WebSocket = MockWebSocket as any

// Mock navigator.wakeLock
Object.defineProperty(navigator, 'wakeLock', {
  value: {
    request: vi.fn().mockResolvedValue({
      released: false,
      type: 'screen',
      release: vi.fn().mockResolvedValue(undefined),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  },
  writable: true,
})
