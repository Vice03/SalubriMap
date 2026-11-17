// SPDX-License-Identifier: AGPL-3.0-or-later
import { Bell, Download, FileUp, LogIn, LogOut, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { askLogin, roleLabel, useSession } from '../../api/session'
import { RoleButton } from '../ui/RoleButton'
import { loadAlerts } from '../../lib/alerts'
import { ago } from '../../lib/format'
import { useApi, useApp } from '../../state/app'
import { ImportDialog } from '../reports/ImportDialog'

const LEVEL = { red: '#dc2626', orange: '#f28c28', blue: '#2563eb', green: '#16a34a' }

function centroid(coords: unknown): [number, number] {
  const flat: number[][] = []
  const walk = (c: unknown) => { if (Array.isArray(c) && typeof c[0] === 'number') flat.push(c as number[]); else if (Array.isArray(c)) c.forEach(walk) }
  walk(coords)
  const x = flat.reduce((s, p) => s + p[0], 0) / flat.length
  const y = flat.reduce((s, p) => s + p[1], 0) / flat.length
  return [x, y]
}

export function Topbar() {
  const nav = useNavigate()
  const { scenarios, scenario, setScenarioId } = useApp()
  const [q, setQ] = useState('')
  const [menu, setMenu] = useState<'export' | 'alerts' | null>(null)
  const [importing, setImporting] = useState(false)
  const session = useSession()
  const initials = session ? session.user.display_name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase() : '?'
  const { data: quartiers } = useApi(() => api.quartiers(), [])
  const { data: health } = useApi(() => api.health(), [])
  const { data: alerts } = useApi(() => loadAlerts(scenario), [scenario?.id, scenario?.latest_ready_plan_id])

  const results = useMemo(() => {
    if (q.trim().length < 2 || !quartiers) return []
    const k = q.toLowerCase()
    return quartiers.features.filter((f) => f.properties.name.toLowerCase().includes(k)).slice(0, 6)
  }, [q, quartiers])
  const urgent = (alerts ?? []).filter((a) => a.level === 'red' || a.level === 'orange').length

  return (
    <header className="topbar">
      <div className="search">
        <Search size={18} color="#475569" />
        <input placeholder="Rechercher un quartier…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher un quartier" />
        {results.length > 0 && (
          <div className="search-results">
            {results.map((f) => (
              <button key={f.properties.id} onClick={() => {
                const [x, y] = centroid(f.geometry.coordinates)
                setQ('')
                nav(`/carte?focus=${x.toFixed(5)},${y.toFixed(5)}`)
              }}>{f.properties.name} <span className="muted">· {f.properties.population.toLocaleString('fr-FR')} hab.</span></button>
            ))}
          </div>
        )}
      </div>
      <div className="topbar-right">
        <label className="muted" htmlFor="scn">Scénario</label>
        <select id="scn" className="select" value={scenario?.id ?? ''} onChange={(e) => setScenarioId(e.target.value)}>
          {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}{s.is_baseline ? ' (base)' : ''}</option>)}
        </select>
        <RoleButton need="admin" className="btn primary" onClick={() => setImporting(true)}><FileUp size={16} />Importer</RoleButton>
        <div style={{ position: 'relative' }}>
          <button className="btn ghost" onClick={() => setMenu(menu === 'export' ? null : 'export')}><Download size={16} />Exporter</button>
          {menu === 'export' && (
            <div className="menu" onMouseLeave={() => setMenu(null)}>
              <a href={api.exportUrl('osm')} download>Dépotoirs vérifiés — OSM (JOSM)</a>
              <a href={api.exportUrl('geojson')} download>Dépotoirs vérifiés — GeoJSON</a>
              <a href={api.exportUrl('csv')} download>Dépotoirs vérifiés — CSV (Excel)</a>
            </div>
          )}
        </div>
        <div style={{ position: 'relative' }}>
          <button className="icon-btn" aria-label="Alertes" onClick={() => setMenu(menu === 'alerts' ? null : 'alerts')}>
            <Bell size={22} />{urgent > 0 && <span className="count">{urgent}</span>}
          </button>
          {menu === 'alerts' && (
            <div className="menu" style={{ width: 360 }} onMouseLeave={() => setMenu(null)}>
              {(alerts ?? []).slice(0, 8).map((a) => (
                <div key={a.id} className="list-item" style={{ padding: '8px 10px' }}>
                  <span className="alert-dot" style={{ background: LEVEL[a.level] }} />
                  <span style={{ flex: 1, fontSize: 13.5 }}>{a.text}</span>
                  {a.at && <span className="muted">{ago(a.at)}</span>}
                </div>
              ))}
              {!alerts?.length && <div className="empty">Aucune alerte</div>}
            </div>
          )}
        </div>
        {health?.demo_mode && (
          <span className="demo-badge" title="Compte « demo » et code ouaga2026 connus de tous : ne pas utiliser pour de vraies données">
            Mode démonstration
          </span>
        )}
        {session ? (
          <div className="user-chip" title={`Connecté en tant que ${session.user.display_name} (${roleLabel(session.user.role)})`}>
            <div className="avatar" aria-hidden>{initials}</div>
            <div style={{ lineHeight: 1.2 }}>
              <span className="sr-only">Connecté en tant que </span>
              <b style={{ fontSize: 14, display: 'block' }}>{session.user.display_name}</b>
              <span className={`role-pill ${session.user.role}`}>{roleLabel(session.user.role)}</span>
            </div>
            <button className="icon-btn" aria-label="Se déconnecter" title="Se déconnecter" onClick={() => void api.logout()}><LogOut size={20} /></button>
          </div>
        ) : (
          <div className="user-chip">
            <div className="avatar off" aria-hidden>?</div>
            <button className="btn ghost" onClick={() => void askLogin()}><LogIn size={16} />Se connecter</button>
          </div>
        )}
      </div>
      {importing && <ImportDialog onClose={() => setImporting(false)} />}
    </header>
  )
}
