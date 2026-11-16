// SPDX-License-Identifier: AGPL-3.0-or-later
// Coquille hors ligne de Salubri Go : l'application s'ouvre sans réseau ; les signalements
// attendent dans l'outbox (IndexedDB) et partent au retour du réseau. /api n'est jamais mis en cache.
const CACHE = 'salubri-go-v2'
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['/go/', '/go/index.html', '/go/manifest.webmanifest', '/go/icon.svg'])).then(() => self.skipWaiting()))
})
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()))
})
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || !url.pathname.startsWith('/go/')) return
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match('/go/index.html')))
    return
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)) }
    return res
  })))
})
