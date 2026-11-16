// SPDX-License-Identifier: AGPL-3.0-or-later
import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { PipelineProgress, Toasts } from './components/layout/Feedback'
import { Sidebar } from './components/layout/Sidebar'
import { Topbar } from './components/layout/Topbar'
import { Dashboard } from './pages/Dashboard'
import { AppProvider } from './state/app'

// Pages chargées à la demande : le premier écran ne télécharge que le tableau de bord (réseau 3G).
const MapPage = lazy(() => import('./pages/MapPage').then((m) => ({ default: m.MapPage })))
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })))
const ScenarioPage = lazy(() => import('./pages/ScenarioPage').then((m) => ({ default: m.ScenarioPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((m) => ({ default: m.ComparePage })))
const AuditPage = lazy(() => import('./pages/AuditPage').then((m) => ({ default: m.AuditPage })))

export function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <div className="shell">
          <Sidebar />
          <div className="main">
            <Topbar />
            <Suspense fallback={<div className="content muted">Chargement…</div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/carte" element={<MapPage />} />
              <Route path="/signalements" element={<ReportsPage />} />
              <Route path="/scenario" element={<ScenarioPage />} />
              <Route path="/comparer" element={<ComparePage />} />
              <Route path="/journal" element={<AuditPage />} />
              <Route path="*" element={<Dashboard />} />
            </Routes>
            </Suspense>
          </div>
        </div>
        <PipelineProgress />
        <Toasts />
      </AppProvider>
    </BrowserRouter>
  )
}
