// SPDX-License-Identifier: AGPL-3.0-or-later
import { Flag, Lock } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { askLogin } from '../api/session'
import type { ReportStatus, WasteType } from '../api/types'
import { ReportDrawer } from '../components/reports/ReportDrawer'
import { StatusBadge } from '../components/ui/Overlay'
import { WasteIcon } from '../components/ui/WasteIcon'
import { ago } from '../lib/format'
import { STATUS, STATUS_COLOR, VOLUME, WASTE } from '../lib/labels'
import { useApi } from '../state/app'

const PAGE = 50

export function ReportsPage() {
  const [sp, setSp] = useSearchParams()
  const status = sp.getAll('status') as ReportStatus[]
  const types = sp.getAll('type') as WasteType[]
  const rule = sp.get('rule') ?? ''
  const [page, setPage] = useState(0)
  const [open, setOpen] = useState<string | null>(null)
  const { data: rules } = useApi(() => api.rules(), [])
  const { data, loading } = useApi(() => api.reports({ status, type: types, rule, limit: PAGE, offset: page * PAGE }),
    [status.join(), types.join(), rule, page])

  const toggle = (key: string, value: string) => {
    const cur = sp.getAll(key)
    const next = new URLSearchParams(sp)
    next.delete(key)
    ;(cur.includes(value) ? cur.filter((x) => x !== value) : [...cur, value]).forEach((x) => next.append(key, x))
    setSp(next)
    setPage(0)
  }
  const total = data?.total ?? 0
  return (
    <div className="content">
      <div className="card">
        <div className="card-head"><Flag color="#0f2b55" /><h2>Signalements</h2><span className="spacer" /><span className="muted">{total} résultat(s)</span></div>
        {data?.restricted && (
          <div className="restricted-note">
            <Lock size={16} /> Vue publique : seuls les signalements vérifiés ou nettoyés, sans appareil ni commentaire.
            <button className="btn ghost" onClick={() => void askLogin()}>Se connecter</button>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="chips">
            {(Object.keys(STATUS) as ReportStatus[]).map((s) => (
              <button key={s} className={`chip ${status.includes(s) ? 'on' : ''}`} style={status.includes(s) ? { background: STATUS_COLOR[s], borderColor: STATUS_COLOR[s] } : {}}
                onClick={() => toggle('status', s)}>{STATUS[s]}</button>
            ))}
          </div>
          <div className="chips">
            {(Object.keys(WASTE) as WasteType[]).map((t) => (
              <button key={t} className={`chip ${types.includes(t) ? 'on' : ''}`} style={types.includes(t) ? { background: '#0f2b55', borderColor: '#0f2b55' } : {}}
                onClick={() => toggle('type', t)}><WasteIcon type={t} size={20} />{WASTE[t]}</button>
            ))}
            <select className="select" value={rule} aria-label="Règle déclenchée" onChange={(e) => {
              const next = new URLSearchParams(sp); if (e.target.value) next.set('rule', e.target.value); else next.delete('rule'); setSp(next); setPage(0)
            }}>
              <option value="">Toutes les règles</option>
              {rules?.rules.map((r) => <option key={r.code} value={r.code}>{r.code} — {r.title}</option>)}
            </select>
          </div>
        </div>
      </div>
      <div className="card" style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead><tr><th>Type</th><th>Statut</th><th>Score</th><th>Règles déclenchées</th><th>Volume</th><th>Reçu</th><th>Identifiant</th></tr></thead>
          <tbody>
            {data?.features.map((f) => {
              const r = f.properties
              return (
                <tr key={r.id} className="clickable" onClick={() => setOpen(r.id)}>
                  <td><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><WasteIcon type={r.waste_type} size={30} />{WASTE[r.waste_type]}</div></td>
                  <td><StatusBadge status={r.status} /></td>
                  <td><b>{r.score}</b></td>
                  <td>{r.rule_hits?.length ? r.rule_hits.map((h) => <span key={h.rule + h.detail} className="rule" title={h.detail}>{h.rule} {h.reject ? 'rejet' : h.delta}</span>) : <span className="muted">—</span>}</td>
                  <td>{VOLUME[r.volume_class]}</td>
                  <td>{ago(r.received_at ?? r.reported_at)}</td>
                  <td className="muted">{r.external_id ?? r.id.slice(0, 8)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!loading && !data?.features.length && <div className="empty">Aucun signalement pour ces filtres</div>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>Précédent</button>
          <span className="muted" style={{ alignSelf: 'center' }}>Page {page + 1} / {Math.max(1, Math.ceil(total / PAGE))}</span>
          <button className="btn ghost" disabled={(page + 1) * PAGE >= total} onClick={() => setPage(page + 1)}>Suivant</button>
        </div>
      </div>
      {open && <ReportDrawer id={open} onClose={() => setOpen(null)} onOpen={setOpen} />}
    </div>
  )
}
