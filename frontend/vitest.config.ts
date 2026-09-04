import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Kept separate from vite.config.ts on purpose: this file is not part of any
// tsconfig `include`, so `tsc -b` doesn't typecheck it — which avoids a
// vite-version type clash between the app's vite and the copy vitest bundles.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})