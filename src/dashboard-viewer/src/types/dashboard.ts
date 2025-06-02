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

export interface WebSocketMessage {
  type: 'connected' | 'image_changed' | 'error' | 'pong' | 'sensors_state' | 'sensors_update' | string
  etag?: string
  current_etag?: string
  timestamp?: string
  message?: string
  last_check?: string | null
  js_hash?: string
  hash_changed?: boolean
  sensors?: Array<{
    entity_id: string
    friendly_name: string
    description: string
    value: string
    state: string
    icon: string
    display_type: 'value' | 'state_icon' | 'state_text'
    attributes: Record<string, unknown>
    last_updated: string
  }>
}

export interface ServerStatus {
  is_polling: boolean
  connected_clients: number
  current_etag: string | null
  last_check: string | null
  js_hash: string | null
}
