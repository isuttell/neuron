export interface ImagePollerOptions {
  pollInterval?: number
  fadeDuration?: number
  onError?: (error: Error) => void
}

export interface ETagMonitorOptions {
  pollInterval?: number
  onETagChange?: (newETag: string) => void
  onError?: (error: Error) => void
}

export interface ImageTransitionProps {
  currentImage: string
  nextImage: string | null
  isTransitioning: boolean
  fadeDuration: number
  className?: string
}

export interface DashboardImageProps {
  url: string
  pollInterval?: number
  fadeDuration?: number
  className?: string
}
