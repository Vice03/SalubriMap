// SPDX-License-Identifier: AGPL-3.0-or-later
import '@fontsource/inter/400.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/800.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { isNative } from './server'
import './theme.css'

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)

// Hors ligne : la coquille est mise en cache (pas sur localhost en dev, pour éviter un cache gênant).
if ('serviceWorker' in navigator && import.meta.env.PROD && !isNative()) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/go/sw.js', { scope: '/go/' }).then((reg) => {
      // lot D : une nouvelle version installée pendant qu'une ancienne contrôle la page → avis « Mettre à jour »
      const announce = (sw: ServiceWorker | null) => { if (sw && navigator.serviceWorker.controller) window.dispatchEvent(new CustomEvent('salubri-sw-update', { detail: sw })) }
      announce(reg.waiting)
      reg.addEventListener('updatefound', () => {
        const sw = reg.installing
        sw?.addEventListener('statechange', () => { if (sw.state === 'installed') announce(sw) })
      })
    })
  })
}
