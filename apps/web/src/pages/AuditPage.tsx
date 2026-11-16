// SPDX-License-Identifier: AGPL-3.0-or-later
import { ClipboardList, Lock } from 'lucide-react'
import { api, signIn } from '../api/client'
import { date } from '../lib/format'
import { AUDIT_ACTION } from '../lib/labels'
import { useApi } from '../state/app'

const ENTITY: Record<string, string> = {
  report: 'Signalement', import_batch: 'Import', dump_site: 'Dépotoir', scenario: 'Scénario', vehicle: 'Camion', quartier: 'Quartier',
}

export function AuditPage() {
  const { data, error } = useApi(() => api.audit(300), [])
  return (
    <div className="content">
      <div className="card" style={{ overflowX: 'auto' }}>
        <div className="card-head"><ClipboardList color="#0f2b55" /><h2>Journal des actions</h2></div>
        {error && (
          <div className="restricted-note">
            <Lock size={16} /> Le journal (appareils, notes, comptes) est réservé à la mairie.
            <button className="btn ghost" onClick={() => { if (signIn()) window.location.reload() }}>Se connecter</button>
          </div>
        )}
        <table className="table">
          <thead><tr><th>Date</th><th>Action</th><th>Objet</th><th>Par</th><th>Détail</th></tr></thead>
          <tbody>
            {data?.map((a) => (
              <tr key={a.id}>
                <td>{date(a.at)}</td>
                <td><b>{AUDIT_ACTION[a.action] ?? a.action}</b></td>
                <td>{ENTITY[a.entity] ?? a.entity} <span className="muted">{a.entity_id?.slice(0, 8)}</span></td>
                <td>{a.actor}</td>
                <td className="muted" style={{ maxWidth: 420 }}>{a.after ? Object.entries(a.after).map(([k, v]) => `${k} : ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`).join(' · ') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.length && <div className="empty">Aucune action enregistrée</div>}
      </div>
    </div>
  )
}
