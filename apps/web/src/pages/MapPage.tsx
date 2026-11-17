// SPDX-License-Identifier: AGPL-3.0-or-later
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useSession } from '../api/session'
import type { DumpProps, Feature, PointGeom } from '../api/types'
import { MapView, type Layers } from '../components/map/MapView'
import { ReportDrawer } from '../components/reports/ReportDrawer'
import { useApi, useApp } from '../state/app'
import { DumpDrawer, LayerToggles } from './Dashboard'

// Ligne visible sous la carte (lot 7.5) : ce qui est montré et sous quelle licence.
export const MAP_LICENCE =
  'Données © Équipe Salubri (Hackathon des universités 2026), ODbL 1.0 · Fond de carte © contributeurs OpenStreetMap'
export const PUBLIC_SCOPE = 'Vue publique : signalements vérifiés uniquement, photos masquées. '

export function MapPage() {
  const { scenario } = useApp()
  const session = useSession() // connecté (mairie) : la carte montre aussi les signalements à vérifier
  const [sp] = useSearchParams()
  const focus = sp.get('focus')?.split(',').map(Number) as [number, number] | undefined
  const planId = scenario?.latest_ready_plan_id ?? null
  const { data: commune } = useApi(() => api.commune(), [])
  const { data: quartiers } = useApi(() => api.quartiers(), [])
  const { data: dumps } = useApi(() => api.dumps({ status: ['active', 'recurring'] }), [])
  const { data: reports } = useApi(() => api.reports({ limit: 2000 }), [])
  const { data: points } = useApi(() => (planId ? api.points(planId) : Promise.resolve(null)), [planId])
  const { data: routes } = useApi(() => (planId ? api.routes(planId) : Promise.resolve(null)), [planId])
  const [layers, setLayers] = useState<Layers>({ quartiers: true, dumps: true, reports: false, points: true, routes: true, trucks: true })
  const [reportId, setReportId] = useState<string | null>(null)
  const [dump, setDump] = useState<Feature<PointGeom, DumpProps> | null>(null)
  return (
    <div className="content">
      <div className="card" style={{ padding: 12 }}>
        <div className="map-wrap tall">
          <MapView commune={commune} quartiers={quartiers} dumps={dumps} reports={reports} points={points} routes={routes}
            layers={layers} focus={focus && focus.length === 2 ? focus : null} onReport={setReportId}
            onDump={(id) => setDump(dumps?.features.find((f) => f.properties.id === id) ?? null)} />
          <LayerToggles layers={layers} setLayers={setLayers} />
        </div>
        <p className="muted map-licence" data-testid="map-licence">{session ? '' : PUBLIC_SCOPE}{MAP_LICENCE}</p>
      </div>
      {reportId && <ReportDrawer id={reportId} onClose={() => setReportId(null)} onOpen={setReportId} />}
      {dump && <DumpDrawer f={dump} onClose={() => setDump(null)} />}
    </div>
  )
}
