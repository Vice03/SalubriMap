// SPDX-License-Identifier: AGPL-3.0-or-later
import { AlertTriangle, ArrowRight, Plus, Trash2, Truck } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import type { FC, LineGeom, RouteProps, Scenario } from '../../api/types'
import { useApi, useApp } from '../../state/app'

export function FleetPanel({ scenario, routes, compact = false }: { scenario: Scenario | null; routes: FC<LineGeom, RouteProps> | null; compact?: boolean }) {
  const nav = useNavigate()
  const { track, toast, reloadScenarios } = useApp()
  const { data: kinds } = useApi(() => api.vehicleKinds(), [])
  const [kind, setKind] = useState('truck_8t')
  const [busy, setBusy] = useState(false)
  if (!scenario) return <div className="card"><div className="empty">Chargement…</div></div>
  const byLabel = new Map<string, RouteProps[]>()
  for (const f of routes?.features ?? []) byLabel.set(f.properties.vehicle_label, [...(byLabel.get(f.properties.vehicle_label) ?? []), f.properties])
  const toggle = async (vid: string, out: boolean, label: string) => {
    try {
      const r = await api.breakdown(scenario.id, vid, out)
      toast('info', `${label} ${out ? 'mis en panne' : 'réparé'} : recalcul du plan`)
      track(r.plan_version_id, 'fleet_changed')
      void reloadScenarios()
    } catch (e) { toast('error', (e as Error).message) }
  }
  const run = async (fn: () => Promise<{ plan_version_id: string }>, msg: string) => {
    setBusy(true)
    try {
      const r = await fn()
      toast('info', `${msg} : recalcul du plan`)
      track(r.plan_version_id, 'fleet_changed')
      await reloadScenarios()
    } catch (e) { toast('error', (e as Error).message) } finally { setBusy(false) }
  }
  const remove = (vid: string, label: string) => {
    if (!window.confirm(`Retirer ${label} de la flotte ? Les tournées seront recalculées sans ce camion.`)) return
    void run(() => api.removeVehicle(scenario.id, vid), `${label} retiré`)
  }
  const active = scenario.vehicles.filter((v) => !v.out_of_service).length
  return (
    <div className="card">
      <div className="card-head">
        <Truck color="#0f2b55" /><h2>État de la flotte</h2>
        <span className="muted" style={{ marginLeft: 8 }}>{active}/{scenario.vehicles.length} en service</span><span className="spacer" />
        {!compact && <button className="link" onClick={() => nav('/scenario')}>Voir tout <ArrowRight size={14} /></button>}
      </div>
      {scenario.vehicles.map((v) => {
        const rs = byLabel.get(v.label) ?? []
        const load = rs.reduce((s, r) => s + r.load_t, 0)
        const ratio = rs.length ? Math.min(1, load / (v.capacity_t * rs.length)) : 0
        const state = v.out_of_service ? { t: 'En panne', c: '#dc2626' } : rs.length ? { t: `En tournée · ${rs.length} rotation${rs.length > 1 ? 's' : ''}`, c: '#16a34a' } : { t: 'Disponible', c: '#2563eb' }
        const color = v.out_of_service ? '#dc2626' : '#1e3a8a'
        return (
          <div key={v.id} className="truck">
            <div className="truck-icon" style={{ background: v.out_of_service ? '#fee2e2' : `${color}1f` }}>
              {v.out_of_service ? <AlertTriangle color="#dc2626" /> : <Truck color={color} size={26} />}
            </div>
            <div className="truck-body">
              <div className="truck-name">{v.label} <span className="muted">· {v.capacity_t} t</span></div>
              <div className="truck-state" style={{ color: state.c }}><span className="alert-dot" style={{ background: state.c }} />{state.t}</div>
              <div className="bar"><span style={{ width: `${v.out_of_service ? 0 : rs.length ? ratio * 100 : 100}%`, background: v.out_of_service ? '#dc2626' : rs.length ? '#16a34a' : '#2563eb' }} /></div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
              <span className="truck-pct">{v.out_of_service ? '0 %' : rs.length ? `${Math.round(ratio * 100)} %` : '—'}</span>
              <div style={{ display: 'flex', gap: 4 }}>
                <button className={`toggle ${v.out_of_service ? '' : 'danger'}`} disabled={busy} onClick={() => void toggle(v.id, !v.out_of_service, v.label)}>
                  {v.out_of_service ? 'Réparer' : 'Panne'}
                </button>
                <button className="toggle" title={`Retirer ${v.label} de la flotte`} disabled={busy || scenario.vehicles.length <= 1}
                  onClick={() => remove(v.id, v.label)}><Trash2 size={13} /></button>
              </div>
            </div>
          </div>
        )
      })}
      <div className="fleet-add">
        <select value={kind} onChange={(e) => setKind(e.target.value)} disabled={busy}>
          {Object.entries(kinds ?? { truck_8t: { label: 'Benne 8 t' } }).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <button className="btn primary" disabled={busy} onClick={() => void run(() => api.addVehicle(scenario.id, kind), `${kinds?.[kind]?.label ?? 'Camion'} ajouté`)}>
          <Plus size={16} />Ajouter un camion
        </button>
      </div>
    </div>
  )
}
