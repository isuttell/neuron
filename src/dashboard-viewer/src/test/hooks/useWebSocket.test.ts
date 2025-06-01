import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWebSocket } from '@/hooks/useWebSocket'

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset WebSocket instances
    ;(global.WebSocket as any).mock.instances.length = 0
  })

  it('should connect to WebSocket and update state', async () => {
    const mockOnMessage = vi.fn()
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:8000/ws', { onMessage: mockOnMessage })
    )

    // Initially not connected
    expect(result.current.isConnected).toBe(false)
    expect(result.current.error).toBe(null)

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    // Should be connected
    expect(result.current.isConnected).toBe(true)
  })

  it('should handle incoming messages', async () => {
    const mockOnMessage = vi.fn()
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:8000/ws', { onMessage: mockOnMessage })
    )

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    // Simulate receiving a message
    const mockMessage = {
      type: 'image_changed',
      etag: 'new-etag',
      timestamp: new Date().toISOString()
    }

    await act(async () => {
      // Get the WebSocket instance and simulate a message
      const ws = (global.WebSocket as any).mock.instances[0]
      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', {
          data: JSON.stringify(mockMessage)
        }))
      }
    })

    expect(mockOnMessage).toHaveBeenCalledWith(mockMessage)
    expect(result.current.lastMessage).toEqual(mockMessage)
  })

  it('should handle auto-refresh on hash change', async () => {
    const mockReload = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { reload: mockReload },
      writable: true
    })

    const mockOnMessage = vi.fn()
    renderHook(() =>
      useWebSocket('ws://localhost:8000/ws', { onMessage: mockOnMessage })
    )

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    // Simulate pong with hash change
    const pongMessage = {
      type: 'pong',
      js_hash: 'new-hash',
      hash_changed: true
    }

    await act(async () => {
      const ws = (global.WebSocket as any).mock.instances[0]
      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', {
          data: JSON.stringify(pongMessage)
        }))
      }
    })

    expect(mockReload).toHaveBeenCalled()
  })

  it('should not call onMessage for pong messages', async () => {
    const mockOnMessage = vi.fn()
    renderHook(() =>
      useWebSocket('ws://localhost:8000/ws', { onMessage: mockOnMessage })
    )

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    // Simulate pong without hash change
    const pongMessage = {
      type: 'pong',
      js_hash: 'same-hash',
      hash_changed: false
    }

    await act(async () => {
      const ws = (global.WebSocket as any).mock.instances[0]
      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', {
          data: JSON.stringify(pongMessage)
        }))
      }
    })

    // Should not call onMessage for pong
    expect(mockOnMessage).not.toHaveBeenCalled()
  })
})
