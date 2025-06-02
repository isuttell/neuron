import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from '../App'
import { renderWithProviders as render } from './test-utils'

// Mock the DashboardImageWS component
vi.mock('@/components/DashboardImageWS', () => ({
  DashboardImageWS: ({ onConnectionChange }: { onConnectionChange?: (connected: boolean) => void }) => {
    // Simulate connection after mount
    setTimeout(() => {
      onConnectionChange?.(true)
    }, 100)
    return <div data-testid="dashboard-image">Dashboard Image</div>
  }
}))

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset window.location.reload mock
    Object.defineProperty(window, 'location', {
      value: { reload: vi.fn() },
      writable: true
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Control Bar', () => {
    it('should render all control buttons', async () => {
      render(<App />)

      // Check refresh button
      const refreshButton = screen.getByTitle('Refresh page')
      expect(refreshButton).toBeInTheDocument()

      // Check WebSocket indicator
      const wsIndicator = screen.getByTitle(/WebSocket:/)
      expect(wsIndicator).toBeInTheDocument()

      // Check wake lock indicator
      const wakeLockIndicator = screen.getByTitle(/Wake Lock:/)
      expect(wakeLockIndicator).toBeInTheDocument()

      // Wait for async updates
      await waitFor(() => {
        expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
      })
    })

    it('should reload page when refresh button is clicked', async () => {
      const reloadSpy = vi.spyOn(window.location, 'reload')
      render(<App />)

      const refreshButton = screen.getByTitle('Refresh page')
      fireEvent.click(refreshButton)

      expect(reloadSpy).toHaveBeenCalled()

      // Wait for async updates
      await waitFor(() => {
        expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
      })
    })

    it('should show disconnected WebSocket indicator initially', async () => {
      render(<App />)

      const wsIndicator = screen.getByTitle('WebSocket: Disconnected')
      expect(wsIndicator).toBeInTheDocument()

      // Check for WifiOff icon (red)
      const wifiOffIcon = wsIndicator.querySelector('.lucide-wifi-off')
      expect(wifiOffIcon).toBeInTheDocument()
      expect(wifiOffIcon).toHaveClass('text-red-400')

      // Wait for async updates
      await waitFor(() => {
        expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
      })
    })

    it('should show connected WebSocket indicator when connected', async () => {
      render(<App />)

      // Wait for the mock connection
      await waitFor(() => {
        const wsIndicator = screen.getByTitle('WebSocket: Connected')
        expect(wsIndicator).toBeInTheDocument()

        // Check for Wifi icon (green)
        const wifiIcon = wsIndicator.querySelector('.lucide-wifi')
        expect(wifiIcon).toBeInTheDocument()
        expect(wifiIcon).toHaveClass('text-green-400')
      })
    })
  })

  describe('Wake Lock Status', () => {
    it('should show active wake lock when supported', async () => {
      render(<App />)

      // The test setup already mocks a successful wake lock
      await waitFor(() => {
        const wakeLockIndicator = screen.getByTitle('Wake Lock: active')
        expect(wakeLockIndicator).toBeInTheDocument()

        // Check for Lock icon (green)
        const lockIcon = wakeLockIndicator.querySelector('.lucide-lock')
        expect(lockIcon).toBeInTheDocument()
        expect(lockIcon).toHaveClass('text-green-400')
      })
    })

    it('should show not supported wake lock when API is not available', () => {
      // Temporarily store the original value
      const originalWakeLock = navigator.wakeLock

      // Remove wake lock API
      delete (navigator as { wakeLock?: unknown }).wakeLock

      render(<App />)

      const wakeLockIndicator = screen.getByTitle('Wake Lock: not supported')
      expect(wakeLockIndicator).toBeInTheDocument()

      // Check for LockOpen icon (yellow)
      const lockOpenIcon = wakeLockIndicator.querySelector('.lucide-lock-open')
      expect(lockOpenIcon).toBeInTheDocument()
      expect(lockOpenIcon).toHaveClass('text-yellow-400')

      // Restore original value
      Object.defineProperty(navigator, 'wakeLock', {
        value: originalWakeLock,
        writable: true,
        configurable: true
      })
    })

    it('should show failed wake lock when request fails', async () => {
      // Mock the wake lock request to fail
      const mockRequest = vi.spyOn(navigator.wakeLock, 'request').mockRejectedValue(new Error('Wake lock failed'))

      render(<App />)

      await waitFor(() => {
        const wakeLockIndicator = screen.getByTitle('Wake Lock: failed')
        expect(wakeLockIndicator).toBeInTheDocument()

        // Check for XCircle icon (red)
        const xCircleIcon = wakeLockIndicator.querySelector('.lucide-circle-x')
        expect(xCircleIcon).toBeInTheDocument()
        expect(xCircleIcon).toHaveClass('text-red-400')
      })

      mockRequest.mockRestore()
    })

    it('should show released wake lock when lock is released', async () => {
      // Create a custom mock wake lock for this test
      let releaseCallback: (() => void) | null = null
      const mockWakeLock = {
        released: false,
        type: 'screen' as WakeLockType,
        onrelease: null,
        addEventListener: vi.fn((event: string, callback: () => void) => {
          if (event === 'release') {
            releaseCallback = callback
          }
        }),
        removeEventListener: vi.fn(),
        release: vi.fn().mockImplementation(async () => {
          if (releaseCallback) {
            releaseCallback()
          }
        }),
        dispatchEvent: vi.fn()
      }

      const mockRequest = vi.spyOn(navigator.wakeLock, 'request').mockResolvedValue(mockWakeLock as WakeLockSentinel)

      render(<App />)

      // Wait for initial active state
      await waitFor(() => {
        expect(screen.getByTitle('Wake Lock: active')).toBeInTheDocument()
      })

      // Simulate wake lock release by calling the callback
      act(() => {
        if (releaseCallback) {
          releaseCallback()
        }
      })

      await waitFor(() => {
        const wakeLockIndicator = screen.getByTitle('Wake Lock: released')
        expect(wakeLockIndicator).toBeInTheDocument()

        // Check for AlertCircle icon (orange)
        const alertCircleIcon = wakeLockIndicator.querySelector('.lucide-circle-alert')
        expect(alertCircleIcon).toBeInTheDocument()
        expect(alertCircleIcon).toHaveClass('text-orange-400')
      })

      mockRequest.mockRestore()
    })
  })

  describe('Debug Mode', () => {
    it('should show debug button in development mode', () => {
      // Mock development mode
      vi.stubEnv('DEV', true)

      render(<App />)

      const debugButton = screen.getByText('Show Debug')
      expect(debugButton).toBeInTheDocument()
    })

    it('should not show debug button in production mode', () => {
      // Mock production mode
      vi.stubEnv('DEV', false)

      render(<App />)

      const debugButton = screen.queryByText('Show Debug')
      expect(debugButton).not.toBeInTheDocument()
    })

    it('should toggle debug info when debug button is clicked', () => {
      vi.stubEnv('DEV', true)

      render(<App />)

      // Initially debug info should not be visible
      expect(screen.queryByText('Dashboard Debug Info')).not.toBeInTheDocument()

      // Click to show debug
      const debugButton = screen.getByText('Show Debug')
      fireEvent.click(debugButton)

      // Debug info should be visible
      expect(screen.getByText('Dashboard Debug Info')).toBeInTheDocument()
      expect(debugButton).toHaveTextContent('Hide Debug')

      // Click to hide debug
      fireEvent.click(debugButton)

      // Debug info should be hidden
      expect(screen.queryByText('Dashboard Debug Info')).not.toBeInTheDocument()
      expect(debugButton).toHaveTextContent('Show Debug')
    })
  })
})
