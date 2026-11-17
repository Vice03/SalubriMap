// SPDX-License-Identifier: AGPL-3.0-or-later
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const api = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env.SALUBRI_API ?? 'http://localhost:8000'

const SW_TEMPLATE = "// SPDX-License-Identifier: AGPL-3.0-or-later\n// Coquille hors ligne de Salubri Go, générée au build (vite.config.ts) avec la liste complète des fichiers :\n// l'application s'ouvre sans réseau dès la première visite. /api n'est jamais mis en cache.\nconst CACHE = 'salubri-go-__VERSION__'\nconst PRECACHE = __PRECACHE__\nself.addEventListener('install', (e) => {\n  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => { if (!self.registration.active) return self.skipWaiting() }))\n})\nself.addEventListener('message', (e) => { if (e.data === 'skipWaiting') self.skipWaiting() })\nself.addEventListener('activate', (e) => {\n  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()))\n})\nself.addEventListener('fetch', (e) => {\n  const url = new URL(e.request.url)\n  if (e.request.method !== 'GET' || !url.pathname.startsWith('/go/')) return\n  if (e.request.mode === 'navigate') {\n    e.respondWith(fetch(e.request).catch(() => caches.match('/go/index.html', { ignoreVary: true })))\n    return\n  }\n  // ignoreVary : un relais qui ajoute « Vary: Origin » (vite preview, certains proxys) ne doit pas casser le hors ligne\n  e.respondWith(caches.match(e.request, { ignoreVary: true }).then((hit) => hit || fetch(e.request)))\n})\n"

/** Génère /go/sw.js avec la liste de TOUS les fichiers du build (JS/CSS hachés, polices) à mettre en cache. */
function serviceWorker(): Plugin {
  return {
    name: 'salubri-go-sw',
    apply: 'build',
    generateBundle(_, bundle) {
      const files = ['/go/', '/go/index.html', '/go/manifest.webmanifest', '/go/icon.svg', '/go/icon-192.png', '/go/icon-512.png', '/go/icon-512-maskable.png',
        ...Object.keys(bundle).filter((f) => f !== 'index.html').map((f) => `/go/${f}`)]
      const version = Date.now().toString(36)
      const src = SW_TEMPLATE.replace('__PRECACHE__', JSON.stringify(files)).replace('__VERSION__', version)
      this.emitFile({ type: 'asset', fileName: 'sw.js', source: src })
    },
  }
}

// Servi par nginx sous /go/ ; en dev, /api et /photos sont relayés vers l'API.
export default defineConfig({
  base: '/go/',
  plugins: [react(), serviceWorker()],
  server: { port: 5174, host: true, proxy: { '/api': api, '/photos': api } },
  preview: { port: 4174, proxy: { '/api': api, '/photos': api } },
})
