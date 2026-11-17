// SPDX-License-Identifier: AGPL-3.0-or-later
import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { LoginHost } from './components/auth/LoginPanel'
import { PipelineProgress, Toasts } from './components/layout/Feedback'
import { PageBoundary } from './components/layout/PageBoundary'
import { Sidebar } from './components/layout/Sidebar'
import { Topbar } from './components/layout/Topbar'
import { Dashboard } from './pages/Dashboard'
import { AppProvider } from './state/app'
import { AssistantPanel } from './modules/assistant/AssistantPanel'
import { useModules } from './modules/useModules'

// Pages chargées à la demande : le premier écran ne télécharge que le tableau de bord (réseau 3G).
const MapPage = lazy(() => import('./pages/MapPage').then((m) => ({ default: m.MapPage })))
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })))
const ScenarioPage = lazy(() => import('./pages/ScenarioPage').then((m) => ({ default: m.ScenarioPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((m) => ({ default: m.ComparePage })))
const AuditPage = lazy(() => import('./pages/AuditPage').then((m) => ({ default: m.AuditPage })))

export function App() {
  const modules = useModules() // modules optionnels : cachés tant qu'ils sont éteints
  return (
    <BrowserRouter>
      <AppProvider>
        <div className="shell">
          <Sidebar />
          <div className="main">
            <Topbar />
            <Suspense fallback={<div className="content muted">Chargement…</div>}>
            <Routes>
              <Route path="/" element={<PageBoundary><Dashboard /></PageBoundary>} />
              <Route path="/carte" element={<PageBoundary><MapPage /></PageBoundary>} />
              <Route path="/signalements" element={<PageBoundary><ReportsPage /></PageBoundary>} />
              <Route path="/scenario" element={<PageBoundary><ScenarioPage /></PageBoundary>} />
              <Route path="/comparer" element={<PageBoundary><ComparePage /></PageBoundary>} />
              <Route path="/journal" element={<PageBoundary><AuditPage /></PageBoundary>} />
              <Route path="*" element={<PageBoundary><Dashboard /></PageBoundary>} />
            </Routes>
            </Suspense>
          </div>
        </div>
        <PipelineProgress />
        <Toasts />
        <LoginHost />
        {modules.assistant && <AssistantPanel />}
      </AppProvider>
    </BrowserRouter>
  )
}
