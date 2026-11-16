// SPDX-License-Identifier: AGPL-3.0-or-later
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const api = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env.SALUBRI_API ?? 'http://localhost:8000'

// Servi par nginx sous /go/ ; en dev, /api et /photos sont relayés vers l'API.
export default defineConfig({
  base: '/go/',
  plugins: [react()],
  server: { port: 5174, host: true, proxy: { '/api': api, '/photos': api } },
  preview: { port: 4174, proxy: { '/api': api, '/photos': api } },
})
