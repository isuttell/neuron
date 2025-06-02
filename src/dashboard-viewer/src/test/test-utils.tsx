import React, { PropsWithChildren } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import sensorReducer from '../store/sensorSlice'
import connectionReducer from '../store/connectionSlice'

// Create a test store
export const createTestStore = (preloadedState?: Partial<ReturnType<typeof configureStore>['getState']>) => {
  return configureStore({
    reducer: {
      sensors: sensorReducer,
      connection: connectionReducer
    },
    preloadedState
  })
}

interface ExtendedRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  preloadedState?: Partial<ReturnType<typeof createTestStore>['getState']>
  store?: ReturnType<typeof createTestStore>
}

// Test wrapper component
const AllTheProviders = ({ children, store }: PropsWithChildren<{ store: ReturnType<typeof createTestStore> }>) => {
  return (
    <Provider store={store}>
      {children}
    </Provider>
  )
}

// Custom render function
export const renderWithProviders = (
  ui: React.ReactElement,
  {
    preloadedState = {},
    store = createTestStore(preloadedState),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) => {
  const Wrapper = ({ children }: PropsWithChildren) => (
    <AllTheProviders store={store}>{children}</AllTheProviders>
  )

  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) }
}

export * from '@testing-library/react'
export { renderWithProviders as render }
