// SPDX-License-Identifier: AGPL-3.0-or-later
import { Check, RotateCcw, ShieldAlert, X } from 'lucide-react'
import { api } from '../../api/client'
import type { ReportStatus } from '../../api/types'
import { ago, num } from '../../lib/format'
import { STATUS_COLOR, VOLUME, WASTE } from '../../lib/labels'
import { useApi, useApp } from '../../state/app'
import { Drawer, StatusBadge } from '../ui/Overlay'
import { WasteIcon } from '../ui/WasteIcon'

export function ReportDrawer({ id, onClose, onOpen }: { id: string; onClose: () => void; onOpen: (id: string) => void }) {
  const { toast, refresh } = useApp()
  const { data, error, reload } = useApi(() => api.report(id), [id])
  const r = data?.properties
  const act = async (fn: () => Promise<unknown>, msg: string) => {
    try { await fn(); toast('ok', msg); reload(); refresh() } catch (e) { toast('error', (e as Error).message) }
  }
  const set = (s: ReportStatus, msg: string) => act(() => api.moderate(id, s), msg)
  return (
    <Drawer title={r ? `Signalement ${r.external_id ?? r.id.slice(0, 8)}` : 'Signalement'} onClose={onClose}>
      {error && <div className="empty">{error}</div>}
      {r && (
        <>
          {r.photo_url
            ? <img src={r.photo_url} alt="Photo du dépotoir" style={{ width: '100%', borderRadius: 12, maxHeight: 260, objectFit: 'cover' }} />
            : <div className="empty" style={{ background: '#f1f5f9', borderRadius: 12 }}>Pas de photo</div>}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div className="gauge" style={{ background: `conic-gradient(${STATUS_COLOR[r.status]} ${r.score * 3.6}deg, #e8edf4 0)` }}><div>{r.score}</div></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <StatusBadge status={r.status} />
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><WasteIcon type={r.waste_type} size={30} /><b>{WASTE[r.waste_type]}</b> · {VOLUME[r.volume_class]}</div>
              <div className="muted">Reçu {ago(r.received_at)} · GPS ± {num(r.gps_accuracy_m ?? 0)} m · appareil {r.device_id ?? '—'}</div>
            </div>
          </div>
          {r.comment && <div style={{ background: '#f8fafd', borderRadius: 10, padding: 10, fontSize: 14 }}>« {r.comment} »</div>}
          <div>
            <h3 style={{ fontSize: 15, marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center' }}><ShieldAlert size={18} color="#b7410e" />Règles anti-pièges</h3>
            {r.rule_hits.length === 0
              ? <div className="muted">Aucune règle déclenchée : le signalement paraît fiable.</div>
              : r.rule_hits.map((h) => (
                <div key={h.rule + h.detail} className="list-item" style={{ alignItems: 'flex-start' }}>
                  <span className="rule">{h.rule}</span>
                  <b style={{ color: h.reject ? '#dc2626' : '#b7410e', minWidth: 46 }}>{h.reject ? 'rejet' : h.delta}</b>
                  <span style={{ fontSize: 14 }}>{h.detail}</span>
                </div>
              ))}
          </div>
          {r.related && r.related.length > 0 && (
            <div>
              <h3 style={{ fontSize: 15, marginBottom: 6 }}>Signalements liés</h3>
              {r.related.map((x) => (
                <button key={x.id} className="link" onClick={() => onOpen(x.id)}>{x.relation === 'original' ? 'Original' : 'Doublon'} {x.id.slice(0, 8)} · score {x.score}</button>
              ))}
            </div>
          )}
          {r.dump_site && <div className="muted">Rattaché au dépotoir {r.dump_site.id.slice(0, 8)} ({r.dump_site.n_reports} signalements)</div>}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn green" onClick={() => void set('verified', 'Signalement vérifié')}><Check size={16} />Vérifier</button>
            <button className="btn red" onClick={() => void set('rejected', 'Signalement rejeté')}><X size={16} />Rejeter</button>
            <button className="btn ghost" onClick={() => void set('to_review', 'Remis à revoir')}>À revoir</button>
            <button className="btn ghost" onClick={() => void act(() => api.revalidate(id), 'Règles rejouées')}><RotateCcw size={16} />Rejouer les règles</button>
          </div>
          {r.forced_status && <div className="muted">Statut forcé par {r.moderated_by ?? 'un modérateur'} {r.moderated_at ? ago(r.moderated_at) : ''}</div>}
        </>
      )}
    </Drawer>
  )
}
