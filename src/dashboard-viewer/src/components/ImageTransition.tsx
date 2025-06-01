import { cn } from '@/lib/utils'
import type { ImageTransitionProps } from '@/types/dashboard'

export function ImageTransition({
  currentImage,
  nextImage,
  isTransitioning,
  fadeDuration,
  className
}: ImageTransitionProps) {
  return (
    <div className={cn("relative w-full h-full overflow-hidden bg-black", className)}>
      {/* Current image layer - fades out during transition */}
      <img
        src={currentImage}
        alt="Dashboard"
        className="absolute inset-0 w-full h-full object-contain"
        style={{
          opacity: isTransitioning && nextImage ? 0 : 1,
          transition: `opacity ${fadeDuration}ms ease-in-out`,
          // Force GPU acceleration for smoother transitions
          transform: 'translateZ(0)',
          backfaceVisibility: 'hidden',
          zIndex: 2
        }}
        // Prevent Firefox from unloading the image
        loading="eager"
        decoding="sync"
      />

      {/* Next image layer - fades in during transition */}
      {nextImage && (
        <img
          src={nextImage}
          alt="Dashboard"
          className="absolute inset-0 w-full h-full object-contain"
          style={{
            opacity: isTransitioning ? 1 : 0,
            transition: `opacity ${fadeDuration}ms ease-in-out`,
            transform: 'translateZ(0)',
            backfaceVisibility: 'hidden',
            zIndex: 1
          }}
          // Prevent Firefox from unloading the image
          loading="eager"
          decoding="sync"
        />
      )}
    </div>
  )
}
