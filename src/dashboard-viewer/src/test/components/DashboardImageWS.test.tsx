import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { DashboardImageWS } from '@/components/DashboardImageWS'
import type { WebSocketMessage } from '@/types/dashboard'

// Mock the useWebSocket hook
vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: false,
    error: null,
    lastMessage: null
  }))
}))

// Mock ImageTransition component
vi.mock('@/components/ImageTransition', () => ({
  ImageTransition: ({ currentImage, nextImage }: { currentImage?: string; nextImage?: string | null }) => {
    return (
      <div data-testid="image-transition">
        {currentImage && <img src={currentImage} alt="Current" />}
        {nextImage && <img src={nextImage} alt="Next" />}
      </div>
    )
  }
}))

// Mock LoadingSpinner component
vi.mock('@/components/LoadingSpinner', () => ({
  LoadingSpinner: ({ className }: { className?: string }) => (
    <div data-testid="loading-spinner" className={className}>Loading...</div>
  )
}))

describe('DashboardImageWS', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Connection Status Callback', () => {
    it('should call onConnectionChange when connection status changes', async () => {
      const mockOnConnectionChange = vi.fn()
      const useWebSocketModule = await import('@/hooks/useWebSocket')
      const mockUseWebSocket = vi.mocked(useWebSocketModule.useWebSocket)

      // Start disconnected
      mockUseWebSocket.mockReturnValue({
        isConnected: false,
        error: null,
        lastMessage: null
      })

      const { rerender } = render(
        <DashboardImageWS
          url="/image"
          onConnectionChange={mockOnConnectionChange}
        />
      )

      // Should report disconnected initially
      expect(mockOnConnectionChange).toHaveBeenCalledWith(false)

      // Update to connected
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        error: null,
        lastMessage: null
      })

      rerender(
        <DashboardImageWS
          url="/image"
          onConnectionChange={mockOnConnectionChange}
        />
      )

      await waitFor(() => {
        expect(mockOnConnectionChange).toHaveBeenCalledWith(true)
      })
    })

    it('should not crash if onConnectionChange is not provided', async () => {
      const useWebSocketModule = await import('@/hooks/useWebSocket')
      const mockUseWebSocket = vi.mocked(useWebSocketModule.useWebSocket)

      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        error: null,
        lastMessage: null
      })

      expect(() => {
        render(<DashboardImageWS url="/image" />)
      }).not.toThrow()
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner when initially loading', async () => {
      render(<DashboardImageWS url="/image" />)

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
    })

    it('should show connection status when not connected during initial load', async () => {
      const useWebSocketModule = await import('@/hooks/useWebSocket')
      const mockUseWebSocket = vi.mocked(useWebSocketModule.useWebSocket)

      mockUseWebSocket.mockReturnValue({
        isConnected: false,
        error: null,
        lastMessage: null
      })

      render(<DashboardImageWS url="/image" />)

      expect(screen.getByText('Connecting to server...')).toBeInTheDocument()
    })
  })

  describe('WebSocket Message Handling', () => {
    it('should handle image_changed message', async () => {
      const useWebSocketModule = await import('@/hooks/useWebSocket')
      const mockUseWebSocket = vi.mocked(useWebSocketModule.useWebSocket)

      let capturedOnMessage: ((message: WebSocketMessage) => void) | undefined

      mockUseWebSocket.mockImplementation((_url, options) => {
        capturedOnMessage = options?.onMessage
        return {
          isConnected: true,
          error: null,
          lastMessage: null
        }
      })

      render(<DashboardImageWS url="/image" />)

      // Simulate image load to exit loading state
      await waitFor(() => {
        const hiddenImage = screen.getByAltText('')
        hiddenImage.dispatchEvent(new Event('load'))
      })

      // Simulate receiving image_changed message
      await waitFor(() => {
        expect(capturedOnMessage).toBeDefined()
      })

      await act(async () => {
        if (capturedOnMessage) {
          capturedOnMessage({
            type: 'image_changed',
            etag: 'new-etag',
            timestamp: new Date().toISOString()
          })
        }
      })

      // Should trigger image reload (new timestamp in URL)
      await waitFor(() => {
        const images = screen.getAllByRole('img')
        const imageWithNewTimestamp = images.find(img =>
          img.getAttribute('src')?.includes('?t=')
        )
        expect(imageWithNewTimestamp).toBeDefined()
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error message when image fails to load', async () => {
      render(<DashboardImageWS url="/image" />)

      // Simulate image error
      await waitFor(() => {
        const hiddenImage = screen.getByAltText('')
        hiddenImage.dispatchEvent(new Event('error'))
      })

      await waitFor(() => {
        expect(screen.getByText('Unable to load dashboard image')).toBeInTheDocument()
      })
    })

    it('should log WebSocket errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const useWebSocketModule = await import('@/hooks/useWebSocket')
      const mockUseWebSocket = vi.mocked(useWebSocketModule.useWebSocket)

      mockUseWebSocket.mockReturnValue({
        isConnected: false,
        error: 'WebSocket connection failed',
        lastMessage: null
      })

      render(<DashboardImageWS url="/image" />)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('WebSocket error:', 'WebSocket connection failed')
      })

      consoleSpy.mockRestore()
    })
  })
})
