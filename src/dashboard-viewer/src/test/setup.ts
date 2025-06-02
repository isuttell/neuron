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

  send(data: string) {
    // Mock implementation - data parameter is used for sending messages
    void data
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
interface MockWebSocketConstructor {
  new (url: string): MockWebSocket
  mock: {
    instances: MockWebSocket[]
  }
}

const MockWebSocketWithMock = MockWebSocket as unknown as MockWebSocketConstructor
MockWebSocketWithMock.mock = {
  instances: mockWebSocketInstances
}

global.WebSocket = MockWebSocket as unknown as typeof WebSocket

// Mock WakeLockSentinel
class MockWakeLockSentinel implements WakeLockSentinel {
  released = false
  type: WakeLockType = 'screen'
  onrelease: ((this: WakeLockSentinel, ev: Event) => void) | null = null
  private listeners: Map<string, ((event: Event) => void)[]> = new Map()

  addEventListener(type: string, listener: (event: Event) => void): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, [])
    }
    this.listeners.get(type)!.push(listener)
  }

  removeEventListener(type: string, listener: (event: Event) => void): void {
    const typeListeners = this.listeners.get(type)
    if (typeListeners) {
      const index = typeListeners.indexOf(listener)
      if (index > -1) {
        typeListeners.splice(index, 1)
      }
    }
  }

  dispatchEvent(event: Event): boolean {
    const typeListeners = this.listeners.get(event.type)
    if (typeListeners) {
      typeListeners.forEach(listener => listener(event))
    }
    return true
  }

  async release(): Promise<void> {
    this.released = true
    this.dispatchEvent(new Event('release'))
  }
}

// Create a mock wake lock instance
const createMockWakeLock = () => new MockWakeLockSentinel()

// Mock navigator.wakeLock
Object.defineProperty(navigator, 'wakeLock', {
  value: {
    request: vi.fn().mockImplementation(() => Promise.resolve(createMockWakeLock())),
  },
  writable: true,
  configurable: true,
})
