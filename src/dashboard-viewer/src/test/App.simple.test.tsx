import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from '../App'

// Mock the DashboardImageWS component
vi.mock('@/components/DashboardImageWS', () => ({
  DashboardImageWS: ({ onConnectionChange }: { onConnectionChange?: (connected: boolean) => void }) => {
    // Call onConnectionChange with false initially to simulate disconnected state
    setTimeout(() => {
      onConnectionChange?.(false)
    }, 0)
    return <div data-testid="dashboard-image">Dashboard Image</div>
  }
}))

describe('App Component - Simple Tests', () => {
  it('should render the dashboard image component', async () => {
    render(<App />)
    expect(screen.getByTestId('dashboard-image')).toBeInTheDocument()

    // Wait for the async state updates to complete
    await waitFor(() => {
      expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
    })
  })

  it('should have control bar with buttons', async () => {
    render(<App />)

    // Check for refresh button
    const refreshButton = screen.getByTitle('Refresh page')
    expect(refreshButton).toBeInTheDocument()

    // Check that there are multiple control elements
    const controlBar = refreshButton.closest('.flex.flex-col')
    expect(controlBar).toBeInTheDocument()

    // Wait for the async state updates to complete
    await waitFor(() => {
      expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
    })
  })

  it('should call window.location.reload when refresh is clicked', async () => {
    const reloadMock = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { reload: reloadMock },
      writable: true
    })

    render(<App />)

    const refreshButton = screen.getByTitle('Refresh page')
    fireEvent.click(refreshButton)

    expect(reloadMock).toHaveBeenCalled()

    // Wait for the async state updates to complete
    await waitFor(() => {
      expect(screen.getByTitle(/Wake Lock:/)).toBeInTheDocument()
    })
  })
})
