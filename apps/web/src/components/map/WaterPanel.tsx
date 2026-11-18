// SPDX-License-Identifier: AGPL-3.0-or-later
import { Droplets, Waves } from 'lucide-react'
import { api } from '../../api/client'
import { num } from '../../lib/format'
import { WASTE } from '../../lib/labels'
import { useApi } from '../../state/app'
import { WATER_DIST_M } from './mapKey'

/** Sous la carte : dépotoirs actifs à moins de WATER_DIST_M m d'une retenue d'eau, par retenue (clic : zoom). */
export function WaterPanel({ onFocus }: { onFocus: (p: [number, number]) => void }) {
  const { data } = useApi(() => api.waterDumps(WATER_DIST_M), [])
  if (!data) return null
  const by = new Map<string, typeof data.sites>()
  for (const s of data.sites) by.set(s.retenue_id, [...(by.get(s.retenue_id) ?? []), s])
  return (
    <div className="card" data-testid="water-panel">
      <div className="card-head">
        <span className="head-icon" style={{ background: 'linear-gradient(135deg,#4fc3f7,#0277bd)' }}><Droplets size={18} color="#fff" /></span>
        <h2>Dépotoirs près des retenues d'eau</h2><span className="spacer" />
        <span className="badge" style={{ background: data.sites.length ? '#e1f5fe' : '#e7f6ec', color: data.sites.length ? '#01579b' : '#1b7a3a' }}>
          {data.sites.length} dépotoir(s) à moins de {data.distance_m} m
        </span>
      </div>
      <p className="muted" style={{ marginTop: -6 }}>
        Au bord d'un barrage ou d'un lac, un dépotoir pollue l'eau (lixiviats, plastiques emportés par les pluies). Retenues : OpenStreetMap.
        Cochez « Retenues d'eau » sur la carte pour les voir cerclés.
      </p>
      {[...by.values()].map((sites) => (
        <div key={sites[0].retenue_id} className="water-group">
          <b>{sites[0].retenue}</b> <span className="muted">· {sites.length} dépotoir(s) · {num(sites.reduce((a, s) => a + s.volume_m3, 0), 1)} m³</span>
          <div className="water-sites">
            {sites.map((s) => (
              <button key={s.id} className="pill-btn" onClick={() => onFocus([s.lon, s.lat])} title="Zoomer sur la carte">
                {s.caniveau && <Waves size={13} color="#c62828" />}{s.distance_m} m · {WASTE[s.type] ?? s.type} · {num(s.volume_m3, 1)} m³{s.statut === 'recurring' ? ' · récidive' : ''}
              </button>
            ))}
          </div>
        </div>
      ))}
      {!data.sites.length && <div className="empty">Aucun dépotoir actif à moins de {data.distance_m} m d'une retenue d'eau.</div>}
    </div>
  )
}
