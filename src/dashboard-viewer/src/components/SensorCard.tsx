import { type SensorState } from '@/store/sensorSlice'
import * as Icons from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState } from 'react'

interface SensorCardProps {
  sensor: SensorState
  className?: string
}

export function SensorCard({ sensor, className }: SensorCardProps) {
  const [isHovered, setIsHovered] = useState(false)

  // Get the icon component from lucide-react
  const getIcon = (iconName: string) => {
    // Convert kebab-case to PascalCase
    const pascalCase = iconName
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join('')

    const Icon = Icons[pascalCase as keyof typeof Icons] as React.FC<{ className?: string }>
    return Icon ? <Icon className="w-6 h-6" /> : <Icons.HelpCircle className="w-6 h-6" />
  }

  return (
    <div className="flex items-center gap-2">
      {/* Value - positioned to the left, right-aligned with fixed width */}
      <div className="text-right min-w-12">
        {sensor.display_type === 'value' && (
          <span className="text-sm font-medium text-white">
            {sensor.value}
          </span>
        )}
        {sensor.display_type === 'state_text' && (
          <span className="text-sm font-medium text-white">
            {sensor.value}
          </span>
        )}
      </div>

      {/* Icon button - same size as control buttons */}
      <div
        className={cn(
          "relative p-2 bg-gray-900 bg-opacity-75 rounded-md",
          "hover:bg-opacity-90 transition-all cursor-pointer",
          "w-10 h-10 flex items-center justify-center",
          className
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        title={`${sensor.friendly_name}: ${sensor.value}`}
      >
        {/* Icon only */}
        <div className="text-white">
          {getIcon(sensor.icon)}
        </div>

        {/* Tooltip on hover - positioned to the left */}
        {isHovered && (
          <div className={cn(
            "absolute right-full top-1/2 transform -translate-y-1/2 mr-2",
            "bg-gray-900 text-white rounded-md p-3 text-sm",
            "shadow-lg border border-gray-700",
            "min-w-max max-w-xs z-50"
          )}>
            <div className="font-medium text-white mb-1">
              {sensor.friendly_name}
            </div>
            <div className="text-gray-300 mb-1">
              {sensor.value}
            </div>
            <div className="text-xs text-gray-400">
              {sensor.description}
            </div>

            {/* Arrow pointing right */}
            <div className="absolute left-full top-1/2 transform -translate-y-1/2">
              <div className="border-t-4 border-b-4 border-l-4 border-transparent border-l-gray-900"></div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
