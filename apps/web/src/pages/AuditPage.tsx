// SPDX-License-Identifier: AGPL-3.0-or-later
import { ClipboardList, Lock } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { askLogin } from '../api/session'
import { auditSentence } from '../lib/auditSentence'
import { date } from '../lib/format'
import { AUDIT_ACTION } from '../lib/labels'
import { useApi } from '../state/app'

const ENTITY: Record<string, string> = {
  report: 'Signalement', import_batch: 'Import', dump_site: 'Dépotoir', scenario: 'Scénario', vehicle: 'Camion', quartier: 'Quartier', user: 'Compte',
}

/** « awa (moderateur) » → nom + rôle lisible */
function Actor({ actor }: { actor: string }) {
  const m = /^(.*) \((moderateur|admin)\)$/.exec(actor)
  if (!m) return <span>{actor}</span>
  return <span>{m[1]} <span className={`role-pill ${m[2]}`}>{m[2] === 'admin' ? 'administrateur' : 'modérateur'}</span></span>
}

export function AuditPage() {
  const { data, error } = useApi(() => api.audit(300), [])
  const [kind, setKind] = useState('')
  const [day, setDay] = useState('')
  const kinds = useMemo(() => [...new Set((data ?? []).map((a) => a.action))].sort(), [data])
  const rows = (data ?? []).filter((a) => (!kind || a.action === kind) && (!day || a.at.slice(0, 10) === day))
  return (
    <div className="content">
      <div className="card" style={{ overflowX: 'auto' }}>
        <div className="card-head"><ClipboardList color="#0f2b55" /><h2>Journal des actions</h2></div>
        {error && (
          <div className="restricted-note">
            <Lock size={16} /> Le journal (appareils, notes, comptes) est réservé à la mairie.
            <button className="btn ghost" onClick={() => void askLogin()}>Se connecter</button>
          </div>
        )}
        {!!data?.length && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
            <select className="select" aria-label="Filtrer par type d'action" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">Toutes les actions</option>
              {kinds.map((k) => <option key={k} value={k}>{AUDIT_ACTION[k] ?? k}</option>)}
            </select>
            <input className="select" type="date" aria-label="Filtrer par date" value={day} onChange={(e) => setDay(e.target.value)} />
            <span className="muted" style={{ alignSelf: 'center' }}>{rows.length} action(s)</span>
          </div>
        )}
        <table className="table">
          <thead><tr><th>Date</th><th>Action</th><th>Objet</th><th>Par</th></tr></thead>
          <tbody>
            {rows.map((a) => {
              const plan = (a.after as Record<string, unknown> | null)?.plan_version_id
              return (
                <tr key={a.id}>
                  <td>{date(a.at)}</td>
                  <td><b>{auditSentence(a)}</b>{typeof plan === 'string' && <> · <Link to="/scenario">plan {plan.slice(0, 8)}</Link></>}</td>
                  <td>{ENTITY[a.entity] ?? a.entity} <span className="muted">{a.entity_id?.slice(0, 8)}</span></td>
                  <td><Actor actor={a.actor} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!rows.length && !error && <div className="empty">Aucune action pour ces filtres</div>}
      </div>
    </div>
  )
}
