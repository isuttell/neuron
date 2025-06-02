import { describe, it, expect, beforeEach, afterEach } from 'vitest'

// Mock process.env for testing
const originalEnv = process.env

describe('Vite configuration', () => {
  beforeEach(() => {
    // Reset process.env before each test
    process.env = { ...originalEnv }
  })

  afterEach(() => {
    // Restore original process.env after each test
    process.env = originalEnv
  })

  it('should use default base path when VITE_BASE_PATH is not set', async () => {
    delete process.env.VITE_BASE_PATH

    // Dynamic import to get fresh config
    const { default: config } = await import('../../vite.config.ts')
    const resolvedConfig = typeof config === 'function' ? config({ command: 'build', mode: 'production' }) : config

    expect(resolvedConfig.base).toBe('/')
  })

  it('should use custom base path when VITE_BASE_PATH is set', async () => {
    process.env.VITE_BASE_PATH = '/dashboard'

    // Dynamic import to get fresh config
    const { default: config } = await import('../../vite.config.ts')
    const resolvedConfig = typeof config === 'function' ? config({ command: 'build', mode: 'production' }) : config

    expect(resolvedConfig.base).toBe('/dashboard')
  })

  it('should handle complex subpaths', async () => {
    process.env.VITE_BASE_PATH = '/api/v1/dashboard'

    // Dynamic import to get fresh config
    const { default: config } = await import('../../vite.config.ts')
    const resolvedConfig = typeof config === 'function' ? config({ command: 'build', mode: 'production' }) : config

    expect(resolvedConfig.base).toBe('/api/v1/dashboard')
  })

  it('should handle empty string base path', async () => {
    process.env.VITE_BASE_PATH = ''

    // Dynamic import to get fresh config
    const { default: config } = await import('../../vite.config.ts')
    const resolvedConfig = typeof config === 'function' ? config({ command: 'build', mode: 'production' }) : config

    expect(resolvedConfig.base).toBe('/')
  })
})
