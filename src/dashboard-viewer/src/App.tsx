import { DashboardImageWS } from '@/components/DashboardImageWS'
import { SensorGrid } from '@/components/SensorGrid'
import { useState, useEffect, useRef } from 'react'
import type { ServerStatus } from '@/types/dashboard'
import { Lock, LockOpen, AlertCircle, XCircle, RotateCw, Wifi, WifiOff, Settings } from 'lucide-react'
import { useAppSelector } from '@/store/hooks'

// Configuration can be passed via environment variables or window object
const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL || '/image'
const FADE_DURATION = parseInt(import.meta.env.VITE_FADE_DURATION || '5000')

function App() {
  const [showDebug, setShowDebug] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null)
  const [wakeLockStatus, setWakeLockStatus] = useState<string>('not supported')
  const [wsConnected, setWsConnected] = useState(false)
  const [showSensors, setShowSensors] = useState(false)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  // Get sensor count from Redux store
  const sensorCount = useAppSelector(state => Object.keys(state.sensors.sensors).length)

  // Request wake lock to prevent screen from sleeping
  useEffect(() => {
    let mounted = true
    const handleVisibilityChange = async () => {
      if (!mounted) return

      if (document.visibilityState === 'visible' && !wakeLockRef.current) {
        try {
          wakeLockRef.current = await navigator.wakeLock.request('screen')
          setWakeLockStatus('active')
        } catch (err) {
          console.error('Failed to re-acquire wake lock:', err)
          setWakeLockStatus('failed')
        }
      }
    }

    const handleRelease = () => {
      if (mounted) {
        setWakeLockStatus('released')
      }
    }

    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator) {
          wakeLockRef.current = await navigator.wakeLock.request('screen')
          setWakeLockStatus('active')

          // Add event listeners
          document.addEventListener('visibilitychange', handleVisibilityChange)
          if (wakeLockRef.current && wakeLockRef.current.addEventListener) {
            wakeLockRef.current.addEventListener('release', handleRelease)
          }
        } else {
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
      mounted = false
      document.removeEventListener('visibilitychange', handleVisibilityChange)

      if (wakeLockRef.current) {
        if (wakeLockRef.current.removeEventListener) {
          wakeLockRef.current.removeEventListener('release', handleRelease)
        }
        if (wakeLockRef.current.release) {
          wakeLockRef.current.release()
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
                className="p-2 bg-gray-900 bg-opacity-75 rounded-md w-10 h-10 flex items-center justify-center"
                title={`Wake Lock: ${wakeLockStatus}`}
              >
                {wakeLockStatus === 'active' && (
                  <Lock className="w-6 h-6 text-green-400" />
                )}
                {wakeLockStatus === 'not supported' && (
                  <LockOpen className="w-6 h-6 text-yellow-400" />
                )}
                {wakeLockStatus === 'failed' && (
                  <XCircle className="w-6 h-6 text-red-400" />
                )}
                {wakeLockStatus === 'released' && (
                  <AlertCircle className="w-6 h-6 text-orange-400" />
                )}
              </div>
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
