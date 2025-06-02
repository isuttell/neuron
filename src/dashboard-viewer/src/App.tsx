import { DashboardImageWS } from '@/components/DashboardImageWS'
import { SensorGrid } from '@/components/SensorGrid'
import { useState, useEffect, useRef } from 'react'
import type { ServerStatus } from '@/types/dashboard'
import { Lock, Ban, AlertCircle, XCircle, RotateCw, Wifi, WifiOff, Settings, Hand, Bug } from 'lucide-react'
import { useAppSelector } from '@/store/hooks'

// Configuration can be passed via environment variables or window object
const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL || '/image'
const FADE_DURATION = parseInt(import.meta.env.VITE_FADE_DURATION || '5000')

function App() {
  const [showDebug, setShowDebug] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null)
  const [wakeLockStatus, setWakeLockStatus] = useState<string>('not supported')
  const [needsUserInteraction, setNeedsUserInteraction] = useState(false)
  const [debugMessages, setDebugMessages] = useState<string[]>([])
  const [showDebugPopup, setShowDebugPopup] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [showSensors, setShowSensors] = useState(false)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  // Get sensor count from Redux store
  const sensorCount = useAppSelector(state => Object.keys(state.sensors.sensors).length)

  // Helper function to add debug messages
  const addDebugMessage = (message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    const fullMessage = `[${timestamp}] ${message}`
    setDebugMessages(prev => [...prev, fullMessage])
  }

  // Handler for user interaction to enable wake lock
  const handleUserInteraction = async () => {
    if (!needsUserInteraction) return

    try {
      if ('wakeLock' in navigator) {
        // Clear any existing wake lock first
        if (wakeLockRef.current && !wakeLockRef.current.released) {
          try {
            await wakeLockRef.current.release()
          } catch {
            // Ignore errors when releasing
          }
        }

        wakeLockRef.current = await navigator.wakeLock.request('screen')
        setWakeLockStatus('active')
        setNeedsUserInteraction(false)

        // Add release handler to this specific wake lock
        if (wakeLockRef.current && wakeLockRef.current.addEventListener) {
          wakeLockRef.current.addEventListener('release', () => {
            setWakeLockStatus('released')
            wakeLockRef.current = null
          })
        }
      }
    } catch (err) {
      console.error('Failed to acquire wake lock after user interaction:', err)
      setWakeLockStatus('failed')
    }
  }

  // Request wake lock to prevent screen from sleeping
  useEffect(() => {
    let mounted = true
    let retryTimeout: number | null = null

    const requestWakeLock = async (): Promise<void> => {
      if (!mounted) return

      try {
        // More detailed API detection
        const hasWakeLock = 'wakeLock' in navigator
        const wakeLockType = typeof navigator.wakeLock
        const navigatorKeys = Object.getOwnPropertyNames(navigator).filter(key => key.includes('wake') || key.includes('Wake')).join(', ')

        // Check if running as PWA
        const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                     (window.navigator as { standalone?: boolean }).standalone === true ||
                     document.referrer.includes('android-app://');

        addDebugMessage(`Wake Lock Check: hasWakeLock=${hasWakeLock}, type=${wakeLockType}, navigator keys with 'wake': [${navigatorKeys}], iOS version: ${navigator.userAgent.match(/OS (\d+_\d+)/)?.[1] || 'unknown'}, isPWA: ${isPWA}, isSecure: ${location.protocol === 'https:'}`)

        if (hasWakeLock) {
          addDebugMessage('Wake Lock API is available')
          // Clear any existing wake lock first
          if (wakeLockRef.current && !wakeLockRef.current.released) {
            try {
              await wakeLockRef.current.release()
            } catch {
              // Ignore errors when releasing
            }
          }

          wakeLockRef.current = await navigator.wakeLock.request('screen')
          setWakeLockStatus('active')
          addDebugMessage('Wake lock acquired successfully!')

          // Add release handler to this specific wake lock
          if (wakeLockRef.current && wakeLockRef.current.addEventListener) {
            wakeLockRef.current.addEventListener('release', handleRelease)
          }
        } else {
          setWakeLockStatus('not supported')
          // Keep the detailed debug message from above instead of overwriting it
        }
      } catch (err) {
        const errorName = err instanceof Error ? err.name : 'unknown'
        const errorMessage = err instanceof Error ? err.message : 'unknown'
        const debugMsg = `Wake Lock Error - Name: ${errorName}, Message: ${errorMessage}`
        addDebugMessage(debugMsg)

        // Check if it's a permission/user interaction error
        if (err instanceof Error && (
          err.name === 'NotAllowedError' ||
          err.message.includes('Permission was denied') ||
          err.message.includes('user interaction') ||
          err.message.includes('not allowed')
        )) {
          setWakeLockStatus('needs interaction')
          setNeedsUserInteraction(true)
          addDebugMessage(debugMsg + ' → Setting to needs interaction')
        } else {
          // Check if we're on a mobile device and API exists - assume user interaction needed
          const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent)
          const userAgent = navigator.userAgent
          if (isMobile && 'wakeLock' in navigator) {
            setWakeLockStatus('needs interaction')
            setNeedsUserInteraction(true)
            addDebugMessage(debugMsg + ` → Mobile detected (${userAgent.slice(0, 50)}), assuming needs interaction`)
          } else {
            setWakeLockStatus('failed')
            addDebugMessage(debugMsg + ` → Not mobile or no API (${userAgent.slice(0, 50)})`)

            // Retry after 5 seconds if the request failed
            if (mounted) {
              retryTimeout = window.setTimeout(() => {
                if (mounted) {
                  requestWakeLock()
                }
              }, 5000)
            }
          }
        }
      }
    }

    const handleVisibilityChange = async () => {
      if (!mounted) return

      // Request wake lock when page becomes visible and we don't have an active one
      if (document.visibilityState === 'visible' &&
          (!wakeLockRef.current || wakeLockRef.current.released)) {
        await requestWakeLock()
      }
    }

    const handleRelease = () => {
      if (mounted) {
        setWakeLockStatus('released')
        wakeLockRef.current = null
        addDebugMessage('Wake lock was released by system')

        // Automatically try to re-acquire wake lock after a brief delay
        // This handles cases where the browser releases the lock due to system policies
        retryTimeout = window.setTimeout(() => {
          if (mounted && document.visibilityState === 'visible') {
            addDebugMessage('Attempting to re-acquire wake lock after release')
            requestWakeLock()
          }
        }, 1000)
      }
    }


    // Set up visibility change listener
    document.addEventListener('visibilitychange', handleVisibilityChange)

    // Initial wake lock request
    addDebugMessage('Starting wake lock initialization')
    requestWakeLock()

    // Cleanup
    return () => {
      mounted = false

      if (retryTimeout) {
        window.clearTimeout(retryTimeout)
      }

      document.removeEventListener('visibilitychange', handleVisibilityChange)

      if (wakeLockRef.current) {
        if (wakeLockRef.current.removeEventListener) {
          wakeLockRef.current.removeEventListener('release', handleRelease)
        }
        if (!wakeLockRef.current.released && wakeLockRef.current.release) {
          wakeLockRef.current.release().catch(() => {
            // Ignore errors during cleanup
          })
        }
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
    <div className="fixed inset-0 bg-black flex flex-col">
      <div className="flex-1 relative">
        <DashboardImageWS
          url={DASHBOARD_URL}
          fadeDuration={FADE_DURATION}
          className="w-full h-full"
          onConnectionChange={setWsConnected}
        />
      </div>

      {/* Control bar - toggle button always visible */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
        {/* Toggle button - always visible */}
        <div className="flex items-center gap-2">
          <div className="min-w-12"></div>
          <button
            onClick={() => setShowSensors(!showSensors)}
            className="p-2 bg-gray-900 bg-opacity-75 rounded-md hover:bg-opacity-90 transition-all cursor-pointer w-10 h-10 flex items-center justify-center"
            title="Toggle control panel"
            type="button"
          >
            <Settings className="w-6 h-6 text-white" />
          </button>
        </div>

        {/* All controls - slide animation */}
        <div className={`overflow-hidden transition-all duration-300 ease-in-out ${
          showSensors ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}>
          {/* Control icons */}
          <div className={`transform transition-transform duration-300 ease-in-out ${
            showSensors ? 'translate-x-0' : 'translate-x-full'
          } flex flex-col gap-2`}>
            {/* Refresh button */}
            <div className="flex items-center gap-2">
              <div className="min-w-12"></div>
              <button
                onClick={() => window.location.reload()}
                className="p-2 bg-gray-900 bg-opacity-75 rounded-md hover:bg-opacity-90 transition-all cursor-pointer w-10 h-10 flex items-center justify-center"
                title="Refresh page"
                type="button"
              >
                <RotateCw className="w-6 h-6 text-white" />
              </button>
            </div>

            {/* WebSocket connection indicator */}
            <div className="flex items-center gap-2">
              <div className="min-w-12"></div>
              <div
                className="p-2 bg-gray-900 bg-opacity-75 rounded-md w-10 h-10 flex items-center justify-center"
                title={`WebSocket: ${wsConnected ? 'Connected' : 'Disconnected'}`}
              >
                {wsConnected ? (
                  <Wifi className="w-6 h-6 text-green-400" />
                ) : (
                  <WifiOff className="w-6 h-6 text-red-400" />
                )}
              </div>
            </div>

            {/* Wake lock indicator */}
            <div className="flex items-center gap-2">
              <div className="min-w-12"></div>
              <div
                className={`p-2 bg-gray-900 bg-opacity-75 rounded-md w-10 h-10 flex items-center justify-center ${
                  needsUserInteraction ? 'cursor-pointer hover:bg-opacity-90 transition-all' : ''
                }`}
                title={
                  needsUserInteraction
                    ? 'Wake Lock: Tap to enable'
                    : `Wake Lock: ${wakeLockStatus}`
                }
                onClick={needsUserInteraction ? handleUserInteraction : undefined}
              >
                {wakeLockStatus === 'active' && (
                  <Lock className="w-6 h-6 text-green-400" />
                )}
                {wakeLockStatus === 'not supported' && (
                  <Ban className="w-6 h-6 text-gray-400" />
                )}
                {wakeLockStatus === 'needs interaction' && (
                  <Hand className="w-6 h-6 text-blue-400 animate-pulse" />
                )}
                {wakeLockStatus === 'failed' && (
                  <XCircle className="w-6 h-6 text-red-400" />
                )}
                {wakeLockStatus === 'released' && (
                  <AlertCircle className="w-6 h-6 text-orange-400" />
                )}
              </div>
            </div>

            {/* Debug log button */}
            <div className="flex items-center gap-2">
              <div className="min-w-12"></div>
              <button
                onClick={() => setShowDebugPopup(!showDebugPopup)}
                className="p-2 bg-gray-900 bg-opacity-75 rounded-md hover:bg-opacity-90 transition-all cursor-pointer w-10 h-10 flex items-center justify-center"
                title={`Debug Log (${debugMessages.length} messages)`}
                type="button"
              >
                <Bug className={`w-6 h-6 ${debugMessages.length > 0 ? 'text-yellow-400' : 'text-gray-400'}`} />
              </button>
            </div>

            {/* Sensors with divider */}
            {sensorCount > 0 && (
              <>
                {/* Divider */}
                <div className="flex items-center gap-2">
                  <div className="min-w-12"></div>
                  <div className="h-px bg-gray-600 bg-opacity-50 w-10"></div>
                </div>

                {/* Sensors */}
                <SensorGrid />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Debug toggle - only visible in development */}
      {import.meta.env.DEV && (
        <button
          onClick={() => setShowDebug(!showDebug)}
          className="absolute top-16 right-4 px-4 py-2 bg-gray-800 text-white rounded-md text-sm opacity-50 hover:opacity-100 transition-opacity"
        >
          {showDebug ? 'Hide' : 'Show'} Debug
        </button>
      )}

      {/* Debug Log Popup */}
      {showDebugPopup && (
        <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 bg-black bg-opacity-95 text-white p-4 rounded-lg max-w-lg w-full mx-4 max-h-96 overflow-hidden flex flex-col">
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-bold text-yellow-400">Debug Log ({debugMessages.length})</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setDebugMessages([])}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-700 rounded"
              >Clear</button>
              <button
                onClick={() => setShowDebugPopup(false)}
                className="text-gray-400 hover:text-white ml-2 text-lg"
              >×</button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto space-y-1 text-xs">
            {debugMessages.length === 0 ? (
              <p className="text-gray-400 italic">No debug messages yet</p>
            ) : (
              debugMessages.map((msg, index) => (
                <p key={index} className="text-green-400 font-mono break-words">{msg}</p>
              ))
            )}
          </div>
          <div className="mt-3 pt-2 border-t border-gray-700 text-xs">
            <p><span className="text-gray-400">Wake Lock Status:</span> <span className="text-blue-400">{wakeLockStatus}</span></p>
            <p><span className="text-gray-400">Needs Interaction:</span> <span className="text-blue-400">{needsUserInteraction ? 'Yes' : 'No'}</span></p>
          </div>
        </div>
      )}

      {/* Debug info */}
      {showDebug && (
        <div className="absolute top-28 right-4 p-4 bg-gray-900 text-white rounded-md text-xs max-w-md">
          <h3 className="font-bold mb-2">Dashboard Debug Info</h3>
          <div className="space-y-1">
            <p><span className="text-gray-400">URL:</span> {DASHBOARD_URL}</p>
            <p><span className="text-gray-400">Fade Duration:</span> {FADE_DURATION/1000} seconds</p>
            <p className="mt-2 text-green-400">
              Using WebSocket for real-time updates
            </p>
            <hr className="my-2 border-gray-700" />
            <p><span className="text-gray-400">Wake Lock:</span> <span className={
              wakeLockStatus === 'active' ? 'text-green-400' :
              wakeLockStatus === 'failed' ? 'text-red-400' :
              wakeLockStatus === 'needs interaction' ? 'text-blue-400' :
              'text-yellow-400'
            }>{wakeLockStatus}</span></p>
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
