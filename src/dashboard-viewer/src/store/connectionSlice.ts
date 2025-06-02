import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface ConnectionState {
  isConnected: boolean
  currentEtag: string | null
  lastCheck: string | null
  jsHash: string | null
  error: string | null
  serverStatus: {
    isPolling: boolean
    connectedClients: number
    sensorCount: number
    sensorConfigLoaded: boolean
  } | null
}

const initialState: ConnectionState = {
  isConnected: false,
  currentEtag: null,
  lastCheck: null,
  jsHash: null,
  error: null,
  serverStatus: null
}

const connectionSlice = createSlice({
  name: 'connection',
  initialState,
  reducers: {
    setConnected: (state, action: PayloadAction<{
      currentEtag: string | null
      lastCheck: string | null
      jsHash: string | null
    }>) => {
      state.isConnected = true
      state.currentEtag = action.payload.currentEtag
      state.lastCheck = action.payload.lastCheck
      state.jsHash = action.payload.jsHash
      state.error = null
    },
    setDisconnected: (state) => {
      state.isConnected = false
      state.error = null
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload
    },
    updateEtag: (state, action: PayloadAction<string>) => {
      state.currentEtag = action.payload
    },
    setServerStatus: (state, action: PayloadAction<ConnectionState['serverStatus']>) => {
      state.serverStatus = action.payload
    }
  }
})

export const { setConnected, setDisconnected, setError, updateEtag, setServerStatus } = connectionSlice.actions
export default connectionSlice.reducer
