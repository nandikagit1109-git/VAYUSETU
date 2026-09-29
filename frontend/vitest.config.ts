import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Vitest config (section 14 frontend gates). jsdom environment so component
// tests run without a browser; the /api layer is mocked per test.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/__tests__/**/*.test.{ts,tsx}'],
  },
})
