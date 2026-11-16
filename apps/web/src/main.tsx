// SPDX-License-Identifier: AGPL-3.0-or-later
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import '@fontsource/inter/800.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './theme/app.css'

createRoot(document.getElementById('root') as HTMLElement).render(<StrictMode><App /></StrictMode>)
