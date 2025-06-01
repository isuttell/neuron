import { DashboardImageWS } from '@/components/DashboardImageWS'
import { useState, useEffect, useRef } from 'react'
import type { ServerStatus } from '@/types/dashboard'

// Configuration can be passed via environment variables or window object
const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL || '/image'
const FADE_DURATION = parseInt(import.meta.env.VITE_FADE_DURATION || '5000')

function App() {
  const [showDebug, setShowDebug] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null)
  const [wakeLockStatus, setWakeLockStatus] = useState<string>('not supported')
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  // Request wake lock to prevent screen from sleeping
  useEffect(() => {
    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator) {
          wakeLockRef.current = await navigator.wakeLock.request('screen')
          setWakeLockStatus('active')
          console.log('Wake Lock acquired')

          // Re-acquire wake lock if page becomes visible again
          document.addEventListener('visibilitychange', async () => {
            if (document.visibilityState === 'visible' && !wakeLockRef.current) {
              try {
                wakeLockRef.current = await navigator.wakeLock.request('screen')
                setWakeLockStatus('active')
                console.log('Wake Lock re-acquired')
              } catch (err) {
                console.error('Failed to re-acquire wake lock:', err)
                setWakeLockStatus('failed')
              }
            }
          })

          // Listen for wake lock release
          wakeLockRef.current.addEventListener('release', () => {
            console.log('Wake Lock released')
            setWakeLockStatus('released')
          })
        } else {
          console.log('Wake Lock API not supported')
          setWakeLockStatus('not supported')
        }
      } catch (err) {
        console.error('Failed to acquire wake lock:', err)
        setWakeLockStatus('failed')
      }
    }

    requestWakeLock()

    // Cleanup
    return () => {
      if (wakeLockRef.current) {
        wakeLockRef.current.release()
        wakeLockRef.current = null
      }
    }
  }, [])

  // Fetch server status periodically in debug mode
  useEffect(() => {
    if (!showDebug) return

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/status')
        const data = await response.json()
        setServerStatus(data)
      } catch (error) {
        console.error('Failed to fetch status:', error)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [showDebug])

  return (
    <div className="fixed inset-0 bg-black">
      <DashboardImageWS
        url={DASHBOARD_URL}
        fadeDuration={FADE_DURATION}
        className="w-full h-full"
      />

      {/* Debug toggle - only visible in development */}
      {import.meta.env.DEV && (
        <button
          onClick={() => setShowDebug(!showDebug)}
          className="absolute top-4 right-4 px-4 py-2 bg-gray-800 text-white rounded-md text-sm opacity-50 hover:opacity-100 transition-opacity"
        >
          {showDebug ? 'Hide' : 'Show'} Debug
        </button>
      )}

      {/* Debug info */}
      {showDebug && (
        <div className="absolute top-16 right-4 p-4 bg-gray-900 text-white rounded-md text-xs max-w-md">
          <h3 className="font-bold mb-2">Dashboard Debug Info</h3>
          <div className="space-y-1">
            <p><span className="text-gray-400">URL:</span> {DASHBOARD_URL}</p>
            <p><span className="text-gray-400">Fade Duration:</span> {FADE_DURATION/1000} seconds</p>
            <p className="mt-2 text-green-400">
              Using WebSocket for real-time updates
            </p>
            <hr className="my-2 border-gray-700" />
            <p><span className="text-gray-400">Wake Lock:</span> <span className={wakeLockStatus === 'active' ? 'text-green-400' : wakeLockStatus === 'failed' ? 'text-red-400' : 'text-yellow-400'}>{wakeLockStatus}</span></p>
            {serverStatus && (
              <>
                <hr className="my-2 border-gray-700" />
                <p><span className="text-gray-400">Server Polling:</span> {serverStatus.is_polling ? 'Active' : 'Inactive'}</p>
                <p><span className="text-gray-400">Connected Clients:</span> {serverStatus.connected_clients}</p>
                <p><span className="text-gray-400">Current ETag:</span> {serverStatus.current_etag || 'None'}</p>
                <p><span className="text-gray-400">Last Check:</span> {serverStatus.last_check ? new Date(serverStatus.last_check).toLocaleTimeString() : 'Never'}</p>
                <p><span className="text-gray-400">JS Hash:</span> {serverStatus.js_hash || 'None'}</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
