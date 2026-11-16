// SPDX-License-Identifier: AGPL-3.0-or-later
import { AlertTriangle, CloudOff, CloudUpload, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { outbox, type OutboxItem } from '../db'
import { STATUS, VOLUME, WASTE } from '../labels'
import { notify, onOutboxChange, syncOutbox } from '../sync'

function Thumb({ blob }: { blob: Blob | null }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!blob) return
    const u = URL.createObjectURL(blob)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [blob])
  return url ? <img className="thumb" src={url} alt="" /> : <div className="thumb empty">📷</div>
}

export function OutboxPage() {
  const [items, setItems] = useState<OutboxItem[]>([])
  const [syncing, setSyncing] = useState(false)
  useEffect(() => {
    const load = () => void outbox.all().then(setItems)
    load()
    return onOutboxChange(load)
  }, [])
  const pending = items.filter((i) => i.state === 'pending').length
  return (
    <div className="page">
      <div className="card banner">
        {pending ? <CloudOff size={26} color="#b45309" /> : <CloudUpload size={26} color="#16a34a" />}
        <div><b>{pending ? `${pending} en attente d'envoi` : 'Tout est envoyé'}</b><div className="hint">{navigator.onLine ? 'Connecté' : 'Hors ligne : envoi automatique au retour du réseau'}</div></div>
        <button className="btn ghost small" disabled={syncing} onClick={async () => { setSyncing(true); await syncOutbox(); setSyncing(false) }}>
          <RefreshCw size={16} className={syncing ? 'spin' : ''} />Synchroniser
        </button>
      </div>
      {!items.length && <p className="hint center">Aucun signalement pour l'instant.</p>}
      {items.map((i) => {
        const w = WASTE.find((x) => x.k === i.wasteType)
        const st = i.verdict ? STATUS[i.verdict.status] ?? STATUS.pending : null
        return (
          <div key={i.clientId} className="card item">
            <Thumb blob={i.photo} />
            <div className="item-body">
              <b>{w?.emoji} {w?.label ?? i.wasteType}</b> <span className="hint">· {VOLUME.find((v) => v.k === i.volumeClass)?.label}</span>
              <div className="hint">{new Date(i.createdAt).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</div>
              {i.state === 'pending' && <span className="pill" style={{ background: '#fef3c7', color: '#92400e' }}>En attente{i.attempts ? ` · ${i.attempts} essai(s)` : ''}</span>}
              {i.state === 'pending' && i.lastError && <div className="hint">{i.lastError}</div>}
              {i.state === 'error' && <span className="pill" style={{ background: '#fee2e2', color: '#991b1b' }}><AlertTriangle size={12} /> {i.lastError}</span>}
              {st && i.verdict && (
                <>
                  <span className="pill" style={{ background: `${st.color}1a`, color: st.color }}>{st.label} · {i.verdict.score}/100</span>
                  {i.verdict.rule_hits.length > 0 && <ul className="hits">{i.verdict.rule_hits.map((h) => <li key={h.rule}>{h.detail}</li>)}</ul>}
                </>
              )}
            </div>
            {i.state !== 'pending' && <button className="icon" aria-label="Retirer de la liste" onClick={async () => { await outbox.remove(i.clientId); notify() }}><Trash2 size={16} /></button>}
          </div>
        )
      })}
    </div>
  )
}
