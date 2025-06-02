import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface SensorState {
  entity_id: string
  friendly_name: string
  description: string
  value: string
  state: string
  icon: string
  display_type: 'value' | 'state_icon' | 'state_text'
  attributes: Record<string, unknown>
  last_updated: string
}

interface SensorsState {
  sensors: Record<string, SensorState>
  lastUpdate: string | null
  isLoading: boolean
}

const initialState: SensorsState = {
  sensors: {},
  lastUpdate: null,
  isLoading: false
}

const sensorSlice = createSlice({
  name: 'sensors',
  initialState,
  reducers: {
    setSensors: (state, action: PayloadAction<{ sensors: SensorState[], timestamp: string }>) => {
      const { sensors, timestamp } = action.payload
      state.sensors = {}
      sensors.forEach(sensor => {
        state.sensors[sensor.entity_id] = sensor
      })
      state.lastUpdate = timestamp
      state.isLoading = false
    },
    updateSensors: (state, action: PayloadAction<{ sensors: SensorState[], timestamp: string }>) => {
      const { sensors, timestamp } = action.payload
      sensors.forEach(sensor => {
        state.sensors[sensor.entity_id] = sensor
      })
      state.lastUpdate = timestamp
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload
    },
    clearSensors: (state) => {
      state.sensors = {}
      state.lastUpdate = null
      state.isLoading = false
    }
  }
})

export const { setSensors, updateSensors, setLoading, clearSensors } = sensorSlice.actions
export default sensorSlice.reducer
