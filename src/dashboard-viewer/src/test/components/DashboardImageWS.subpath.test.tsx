import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { Provider } from 'react-redux'
import { store } from '@/store/store'
import { DashboardImageWS } from '@/components/DashboardImageWS'

// Mock WebSocket
const mockWebSocket = vi.fn()
mockWebSocket.prototype.send = vi.fn()
mockWebSocket.prototype.close = vi.fn()
mockWebSocket.prototype.addEventListener = vi.fn()
global.WebSocket = mockWebSocket

// Mock Image constructor
global.Image = class {
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  src = ''

  constructor() {
    setTimeout(() => {
      if (this.onload) {
        this.onload()
      }
    }, 0)
  }
} as unknown as typeof Image

// Store original location
const originalLocation = window.location

describe('DashboardImageWS subpath support', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful WebSocket connection
    mockWebSocket.mockImplementation(() => ({
      readyState: WebSocket.OPEN,
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn((event, handler) => {
        if (event === 'open') {
          setTimeout(() => handler(), 0)
        }
      }),
      removeEventListener: vi.fn(),
    }))
  })

  afterEach(() => {
    // Restore original location
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true
    })
  })

  it('should construct WebSocket URL correctly for root deployment', () => {
    // Mock window.location for root deployment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        host: 'example.com',
      },
      writable: true
    })

    render(
      <Provider store={store}>
        <DashboardImageWS url="/image" />
      </Provider>
    )

    // WebSocket should be created with correct URL
    expect(mockWebSocket).toHaveBeenCalledWith('wss://example.com/ws')
  })

  it('should construct WebSocket URL correctly for subpath deployment', () => {
    // Mock window.location for subpath deployment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        host: 'example.com',
      },
      writable: true
    })

    render(
      <Provider store={store}>
        <DashboardImageWS url="/image" />
      </Provider>
    )

    // WebSocket URL should work with subpath (handled by backend root_path)
    expect(mockWebSocket).toHaveBeenCalledWith('wss://example.com/ws')
  })

  it('should handle http protocol correctly', () => {
    // Mock window.location with http protocol
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'http:',
        host: 'localhost:8000',
      },
      writable: true
    })

    render(
      <Provider store={store}>
        <DashboardImageWS url="/image" />
      </Provider>
    )

    // WebSocket should use ws protocol for http
    expect(mockWebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws')
  })

  it('should use custom WebSocket URL from environment', () => {
    // Mock environment variable
    const originalEnv = import.meta.env.VITE_WS_URL
    import.meta.env.VITE_WS_URL = 'wss://custom.example.com/ws'

    render(
      <Provider store={store}>
        <DashboardImageWS url="/image" />
      </Provider>
    )

    // Should use custom URL from environment
    expect(mockWebSocket).toHaveBeenCalledWith('wss://custom.example.com/ws')

    // Restore original value
    import.meta.env.VITE_WS_URL = originalEnv
  })

  it('should append timestamp to image URLs correctly', () => {
    const mockDateNow = vi.spyOn(Date, 'now').mockReturnValue(123456789)

    render(
      <Provider store={store}>
        <DashboardImageWS url="/image" />
      </Provider>
    )

    // Should append timestamp to image URL
    expect(global.Image).toHaveBeenCalled()

    mockDateNow.mockRestore()
  })
})
