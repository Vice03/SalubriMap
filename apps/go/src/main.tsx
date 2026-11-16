// SPDX-License-Identifier: AGPL-3.0-or-later
import '@fontsource/inter/400.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/800.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './theme.css'

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)

// Hors ligne : la coquille est mise en cache (pas sur localhost en dev, pour éviter un cache gênant).
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => { void navigator.serviceWorker.register('/go/sw.js', { scope: '/go/' }) })
}
