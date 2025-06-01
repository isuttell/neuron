import { useState } from 'react'
import { useImagePoller } from '@/hooks/useImagePoller'
import { ImageTransition } from './ImageTransition'
import { LoadingSpinner } from './LoadingSpinner'
import { cn } from '@/lib/utils'
import type { DashboardImageProps } from '@/types/dashboard'

export function DashboardImage({
  url,
  pollInterval = 30000,
  fadeDuration = 1000,
  className
}: DashboardImageProps) {
  const [hasError, setHasError] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)

  const { currentImage, nextImage, isTransitioning } = useImagePoller(url, {
    pollInterval,
    fadeDuration,
    onError: (error) => {
      console.error('Dashboard image error:', error)
      // Don't set error state for polling errors - keep showing the image
      // Only set error if the image itself fails to load
    }
  })

  const handleImageLoad = () => {
    console.log('Image loaded successfully:', currentImage)
    setIsInitialLoad(false)
    setHasError(false)
  }

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    console.error('Image failed to load:', currentImage, e)
    setHasError(true)
    setIsInitialLoad(false)
  }

  if (isInitialLoad) {
    return (
      <div className={cn("flex items-center justify-center", className)}>
        <LoadingSpinner className="w-12 h-12" />
        {/* Hidden image to detect load */}
        <img
          src={currentImage}
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
        </div>
      </div>
    )
  }

  return (
    <ImageTransition
      currentImage={currentImage}
      nextImage={nextImage}
      isTransitioning={isTransitioning}
      fadeDuration={fadeDuration}
      className={className}
    />
  )
}
