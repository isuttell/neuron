import { useAppSelector } from '@/store/hooks'
import { SensorCard } from './SensorCard'
import { cn } from '@/lib/utils'

interface SensorGridProps {
  className?: string
}

export function SensorGrid({ className }: SensorGridProps) {
  const sensors = useAppSelector(state => state.sensors.sensors)
  const isLoading = useAppSelector(state => state.sensors.isLoading)

  const sensorList = Object.values(sensors)

  if (isLoading && sensorList.length === 0) {
    return null
  }

  if (sensorList.length === 0) {
    return null
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {sensorList.map(sensor => (
        <SensorCard key={sensor.entity_id} sensor={sensor} />
      ))}
    </div>
  )
}
