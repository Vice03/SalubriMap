// SPDX-License-Identifier: AGPL-3.0-or-later
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const api = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env.SALUBRI_API ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: api, changeOrigin: true },
      '/photos': { target: api, changeOrigin: true },
    },
  },
  build: { chunkSizeWarningLimit: 1500 },
})
