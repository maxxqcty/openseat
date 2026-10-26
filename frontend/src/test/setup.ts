import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

vi.stubGlobal('import.meta', { ...import.meta, env: { ...import.meta.env, VITE_API_MODE: 'mock' } })

afterEach(() => {
  cleanup()
})
