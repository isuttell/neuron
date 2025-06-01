import { useState, useCallback, useRef, useEffect } from 'react'
import { preloadImage } from '@/lib/api'
import { useETagMonitor } from './useETagMonitor'
import type { ImagePollerOptions } from '@/types/dashboard'

export function useImagePoller(imageUrl: string, options?: ImagePollerOptions) {
  const [currentImage, setCurrentImage] = useState<string>(imageUrl)
  const [nextImage, setNextImage] = useState<string | null>(null)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const transitionTimeoutRef = useRef<number | null>(null)
  const imageVersionRef = useRef(0)

  const handleETagChange = useCallback(async () => {
    try {
      // Create versioned URL to bypass browser cache
      imageVersionRef.current += 1
      const versionedUrl = `${imageUrl}?v=${Date.now()}-${imageVersionRef.current}`

      // Preload the new image
      await preloadImage(versionedUrl)

      // Set next image and start transition
      setNextImage(versionedUrl)
      setIsTransitioning(true)

      // After fade duration, swap images
      if (transitionTimeoutRef.current) {
        clearTimeout(transitionTimeoutRef.current)
      }

      transitionTimeoutRef.current = window.setTimeout(() => {
        setCurrentImage(versionedUrl)
        setNextImage(null)
        setIsTransitioning(false)
      }, options?.fadeDuration || 1000)
    } catch (error) {
      console.error('Failed to load new image:', error)
      options?.onError?.(error as Error)
    }
  }, [imageUrl, options])

  const { currentETag } = useETagMonitor({
    url: imageUrl,
    pollInterval: options?.pollInterval,
    onETagChange: handleETagChange,
    onError: options?.onError
  })

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (transitionTimeoutRef.current) {
        clearTimeout(transitionTimeoutRef.current)
      }
    }
  }, [])

  return {
    currentImage,
    nextImage,
    isTransitioning,
    currentETag
  }
}
