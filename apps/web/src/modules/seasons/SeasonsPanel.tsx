// SPDX-License-Identifier: AGPL-3.0-or-later
import type { GeoJSONSource, Map as MLMap, MapMouseEvent } from 'maplibre-gl'
import { useEffect, useState } from 'react'
import { can } from '../../api/session'
import { seasonsApi, type ImportResult, type PlanSeason } from './api'

const PERIODS: Record<string, string> = { rain: 'Saison des pluies', dry: 'Saison sèche' }

function mapInstance(): MLMap | null { return ((window as unknown as { __salubriMap?: MLMap }).__salubriMap) ?? null }

/** Module « Saisons » : couche « Routes » (praticable / impraticable pour la saison choisie), points déplacés en
 *  saison des pluies avec leurs raisons, saisie du modérateur sur la carte, import d'un fichier d'états de routes. */
export function SeasonsPanel({ planId }: { planId: string | null }) {
  const [period, setPeriod] = useState('rain')
  const [roads, setRoads] = useState<GeoJSON.FeatureCollection | null>(null)
  const [plan, setPlan] = useState<PlanSeason | null>(null)
  const [edit, setEdit] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [imp, setImp] = useState<ImportResult | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [tick, setTick] = useState(0)
  const moderator = can('moderateur')

  useEffect(() => { void seasonsApi.roads(period).then(setRoads).catch((e) => setMsg(String(e.message))) }, [period, tick])
  useEffect(() => { if (planId) void seasonsApi.plan(planId).then(setPlan).catch(() => setPlan(null)) }, [planId, tick])

  // couche « Routes » sur la carte existante
  useEffect(() => {
    const draw = () => {
      const m = mapInstance()
      if (!m || !roads || !m.isStyleLoaded()) return
      const src = m.getSource('season-roads') as GeoJSONSource | undefined
      if (src) src.setData(roads)
      else {
        m.addSource('season-roads', { type: 'geojson', data: roads })
        m.addLayer({ id: 'season-roads', type: 'line', source: 'season-roads', layout: { 'line-cap': 'round' },
          paint: { 'line-width': 5, 'line-color': ['case', ['get', 'passable'], '#f59e0b', '#dc2626'], 'line-dasharray': [2, 1] } })
      }
    }
    draw()
    window.addEventListener('salubri:map-ready', draw)
    return () => window.removeEventListener('salubri:map-ready', draw)
  }, [roads])
  useEffect(() => () => { const m = mapInstance(); if (m?.getLayer('season-roads')) { m.removeLayer('season-roads'); m.removeSource('season-roads') } }, [])

  // saisie du modérateur : un clic sur la carte bascule la route la plus proche
  useEffect(() => {
    const m = mapInstance()
    if (!m || !edit) return
    const onClick = async (e: MapMouseEvent) => {
      try {
        const r = await seasonsApi.near(e.lngLat.lng, e.lngLat.lat)
        const closed = roads?.features.some((f) => f.properties?.road_id === r.road_id && f.properties?.passable === false)
        await seasonsApi.set(r.road_id, period, !!closed)
        setMsg(`Route ${r.highway} ${closed ? 'rouverte' : 'impraticable'} (${PERIODS[period] ?? period}) : les plans de cette saison se recalculent.`)
        setTick((t) => t + 1)
      } catch (err) { setMsg(String((err as Error).message)) }
    }
    m.on('click', onClick)
    m.getCanvas().style.cursor = 'crosshair'
    return () => { m.off('click', onClick); m.getCanvas().style.cursor = '' }
  }, [edit, period, roads])

  const closed = roads?.features.filter((f) => f.properties?.passable === false).length ?? 0
  const moved = plan?.points_deplaces ?? []
  const inacc = plan?.points_inaccessibles ?? []
  return (
    <div className="card" data-testid="seasons-panel" style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <b>Routes</b>
        <select aria-label="Saison de la couche Routes" value={period} onChange={(e) => setPeriod(e.target.value)}>
          {Object.entries(PERIODS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="muted">{closed} route(s) impraticable(s) · <span style={{ color: '#dc2626' }}>━ impraticable</span> · <span style={{ color: '#f59e0b' }}>━ ralentie</span></span>
        {moderator && <label><input type="checkbox" checked={edit} onChange={(e) => setEdit(e.target.checked)} /> Cliquer une route pour la couper / la rouvrir</label>}
      </div>
      {plan && plan.periode === 'rain' && (
        <div style={{ marginTop: 8 }}>
          <b>{moved.length} point(s) déplacé(s) en saison des pluies</b>{inacc.length > 0 && <>, <b style={{ color: '#dc2626' }}>{inacc.length} inaccessible(s)</b></>}
          <ul>
            {moved.map((m) => <li key={m.point}>{m.point} : déplacé de {m.distance_m} m, {m.raison}</li>)}
            {inacc.map((m) => <li key={m.point}>{m.point} : {m.raison} ({m.menages} ménages)</li>)}
          </ul>
        </div>
      )}
      {moderator && (
        <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span>Importer des états de routes (CSV ou GeoJSON : osm_id ou lat/lon, saison, praticable)</span>
          <input type="file" accept=".csv,.geojson,.json" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setImp(null) }} />
          <button className="btn" disabled={!file} onClick={() => file && void seasonsApi.importFile(file, true).then(setImp).catch((e) => setMsg(e.message))}>Vérifier</button>
          <button className="btn primary" disabled={!file || !imp} onClick={() => file && void seasonsApi.importFile(file, false).then((r) => { setImp(r); setTick((t) => t + 1) }).catch((e) => setMsg(e.message))}>Importer</button>
          {imp?.batch_id && <button className="btn" onClick={() => void seasonsApi.undo(imp.batch_id!).then(() => { setImp(null); setTick((t) => t + 1); setMsg('Import annulé') })}>Annuler l'import</button>}
        </div>
      )}
      {imp && <p className="muted">{imp.accepted} ligne(s) acceptée(s), {imp.rejected} refusée(s){imp.report.filter((r) => r.status === 'rejected').slice(0, 5).map((r) => ` · ligne ${r.row} : ${(r.errors ?? []).join(', ')}`).join('')}</p>}
      {msg && <p className="muted" role="status">{msg}</p>}
    </div>
  )
}
