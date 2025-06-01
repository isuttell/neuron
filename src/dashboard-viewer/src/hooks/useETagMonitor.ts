import { useState, useEffect, useRef, useCallback } from 'react'
import { checkETag } from '@/lib/api'
import type { ETagMonitorOptions } from '@/types/dashboard'

const MAX_RETRY_DELAY = 5 * 60 * 1000 // 5 minutes
const INITIAL_RETRY_DELAY = 5000 // 5 seconds

export function useETagMonitor({
  url,
  pollInterval = 30000,
  onETagChange,
  onError
}: ETagMonitorOptions & { url: string }) {
  const [currentETag, setCurrentETag] = useState<string | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [lastError, setLastError] = useState<Error | null>(null)
  const intervalRef = useRef<number | null>(null)
  const mountedRef = useRef(true)

  const checkForUpdate = useCallback(async () => {
    if (!mountedRef.current || isChecking) return

    setIsChecking(true)
    try {
      const newETag = await checkETag(url)

      if (!mountedRef.current) return

      // Success - reset retry count
      setRetryCount(0)
      setLastError(null)

      if (newETag && newETag !== currentETag) {
        if (currentETag === null) {
          // First check, just set the initial ETag without triggering change
          setCurrentETag(newETag)
        } else {
          // Subsequent checks, trigger change event
          setCurrentETag(newETag)
          onETagChange?.(newETag)
        }
      }

      // Schedule next regular check
      if (mountedRef.current) {
        if (intervalRef.current) {
          clearTimeout(intervalRef.current)
        }
        intervalRef.current = window.setTimeout(() => {
          checkForUpdate()
        }, pollInterval)
      }
    } catch (error) {
      if (!mountedRef.current) return

      setLastError(error as Error)

      // Exponential backoff for errors
      const delay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY)
      setRetryCount(prev => prev + 1)

      if (mountedRef.current) {
        if (intervalRef.current) {
          clearTimeout(intervalRef.current)
        }
        intervalRef.current = window.setTimeout(() => {
          checkForUpdate()
        }, delay)
      }

      onError?.(error as Error)
    } finally {
      if (mountedRef.current) {
        setIsChecking(false)
      }
    }
  }, [url, currentETag, isChecking, retryCount, onETagChange, onError, pollInterval])

  useEffect(() => {
    mountedRef.current = true

    // Initial check
    checkForUpdate()

    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearTimeout(intervalRef.current)
      }
    }
  }, []) // Only run on mount

  return {
    currentETag,
    isChecking,
    checkNow: checkForUpdate,
    lastError,
    retryCount
  }
}
