// SPDX-License-Identifier: AGPL-3.0-or-later
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { PipelineProgress, Toasts } from './components/layout/Feedback'
import { Sidebar } from './components/layout/Sidebar'
import { Topbar } from './components/layout/Topbar'
import { AuditPage } from './pages/AuditPage'
import { ComparePage } from './pages/ComparePage'
import { Dashboard } from './pages/Dashboard'
import { MapPage } from './pages/MapPage'
import { ReportsPage } from './pages/ReportsPage'
import { ScenarioPage } from './pages/ScenarioPage'
import { AppProvider } from './state/app'

export function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <div className="shell">
          <Sidebar />
          <div className="main">
            <Topbar />
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/carte" element={<MapPage />} />
              <Route path="/signalements" element={<ReportsPage />} />
              <Route path="/scenario" element={<ScenarioPage />} />
              <Route path="/comparer" element={<ComparePage />} />
              <Route path="/journal" element={<AuditPage />} />
              <Route path="*" element={<Dashboard />} />
            </Routes>
          </div>
        </div>
        <PipelineProgress />
        <Toasts />
      </AppProvider>
    </BrowserRouter>
  )
}
