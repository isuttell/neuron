import { useState, useEffect, useCallback, useRef } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ImageTransition } from './ImageTransition'
import { LoadingSpinner } from './LoadingSpinner'
import { cn } from '@/lib/utils'
import type { DashboardImageProps, WebSocketMessage } from '@/types/dashboard'

export function DashboardImageWS({
  url,
  fadeDuration = 1000,
  className
}: Omit<DashboardImageProps, 'pollInterval'>) {
  const [hasError, setHasError] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const [isTransitioning, setIsTransitioning] = useState(false)

  // Use refs to maintain stable image URLs during transitions
  const currentImageRef = useRef<string>(`${url}?t=${Date.now()}`)
  const nextImageRef = useRef<string | null>(null)
  const [, forceUpdate] = useState({})

  // Get WebSocket URL - use wss for https, ws for http
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = import.meta.env.VITE_WS_URL ||
    `${protocol}//${window.location.host}/ws`;

  const handleImageChange = useCallback(() => {
    // Use timestamp to force reload
    const newUrl = `${url}?t=${Date.now()}`;

    // Preload the new image
    const img = new Image();
    img.onload = () => {
      // Set next image and start transition
      nextImageRef.current = newUrl;
      setIsTransitioning(true);
      forceUpdate({});

      // After transition completes, swap the images
      setTimeout(() => {
        // Move next image to current
        currentImageRef.current = nextImageRef.current!;
        nextImageRef.current = null;
        setIsTransitioning(false);
        forceUpdate({});
      }, fadeDuration);
    };

    img.onerror = () => {
      console.error('Failed to load new image');
    };

    img.src = newUrl;
  }, [url, fadeDuration]);

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'image_updated') {
      handleImageChange();
    }
  }, [handleImageChange]);

  const { isConnected, error: wsError } = useWebSocket(wsUrl, {
    onMessage: handleWebSocketMessage
  });

  const handleImageLoad = () => {
    setIsInitialLoad(false)
    setHasError(false)
  }

  const handleImageError = () => {
    console.error('Image failed to load:', currentImageRef.current)
    setHasError(true)
    setIsInitialLoad(false)
  }

  // Log WebSocket errors only
  useEffect(() => {
    if (wsError) {
      console.error('WebSocket error:', wsError);
    }
  }, [wsError]);

  if (isInitialLoad) {
    return (
      <div className={cn("flex items-center justify-center", className)}>
        <div className="text-center">
          <LoadingSpinner className="w-12 h-12 mb-4" />
          {!isConnected && (
            <p className="text-sm text-gray-400">Connecting to server...</p>
          )}
        </div>
        {/* Hidden image to detect load */}
        <img
          src={currentImageRef.current}
          className="hidden"
          onLoad={handleImageLoad}
          onError={handleImageError}
          alt=""
        />
      </div>
    )
  }

  if (hasError) {
    return (
      <div className={cn("flex items-center justify-center bg-gray-900 text-white", className)}>
        <div className="text-center p-8">
          <p className="text-xl mb-2">Unable to load dashboard image</p>
          <p className="text-sm text-gray-400">Check your connection and try refreshing</p>
          {wsError && (
            <p className="text-xs text-red-400 mt-2">WebSocket: {wsError}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <ImageTransition
      currentImage={currentImageRef.current}
      nextImage={nextImageRef.current}
      isTransitioning={isTransitioning}
      fadeDuration={fadeDuration}
      className={className}
    />
  )
}
