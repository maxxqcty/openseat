import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  define: {
    'import.meta.env.VITE_API_MODE': '"mock"',
    'import.meta.env.DEV': 'true'
  }
})