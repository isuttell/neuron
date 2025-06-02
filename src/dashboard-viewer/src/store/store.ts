import { configureStore } from '@reduxjs/toolkit'
import sensorReducer from './sensorSlice'
import connectionReducer from './connectionSlice'

export const store = configureStore({
  reducer: {
    sensors: sensorReducer,
    connection: connectionReducer
  }
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
