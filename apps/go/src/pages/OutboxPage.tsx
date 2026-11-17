// SPDX-License-Identifier: AGPL-3.0-or-later
import { AlertTriangle, Check, CloudOff, CloudUpload, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { outbox, type OutboxItem } from '../db'
import { STEPS, VOLUME, WASTE, citizenVerdict } from '../labels'
import { notify, onOutboxChange, refreshFollowUp, syncOutbox } from '../sync'

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
    void refreshFollowUp()
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
        const cv = i.verdict ? citizenVerdict(i.verdict.status) : null
        const steps = i.verdict?.steps ?? { recu: !!i.verdict, verifie: i.verdict?.status === 'verified' || i.verdict?.status === 'cleaned', planifie: false, nettoye: i.verdict?.status === 'cleaned' }
        return (
          <div key={i.clientId} className="card item">
            <Thumb blob={i.photo} />
            <div className="item-body">
              <b>{w?.emoji} {w?.label ?? i.wasteType}</b> <span className="hint">· {VOLUME.find((v) => v.k === i.volumeClass)?.label}</span>
              <div className="hint">{new Date(i.createdAt).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</div>
              {i.state === 'pending' && <span className="pill" style={{ background: '#fef3c7', color: '#92400e' }}>En attente{i.attempts ? ` · ${i.attempts} essai(s)` : ''}</span>}
              {i.state === 'pending' && i.lastError && <div className="hint">{i.lastError}</div>}
              {i.state === 'error' && <span className="pill" style={{ background: '#fee2e2', color: '#991b1b' }}><AlertTriangle size={12} /> {i.lastError}</span>}
              {cv && i.verdict && (
                <>
                  <span className="pill" style={{ background: cv.bg, color: cv.color }}>{cv.text}</span>
                  {i.verdict.status !== 'rejected' && (
                    <ol className="timeline" aria-label="Suivi du signalement">
                      {STEPS.map((s) => (
                        <li key={s.k} className={steps[s.k] ? 'done' : ''} aria-current={steps[s.k] ? undefined : 'step'}>
                          <span className="dot">{steps[s.k] && <Check size={11} />}</span>{s.label}
                        </li>
                      ))}
                    </ol>
                  )}
                  {i.verdict.rule_hits.length > 0 && (
                    <details className="why">
                      <summary>Pourquoi ?</summary>
                      <ul className="hits">{i.verdict.rule_hits.map((h) => <li key={h.rule}>{h.detail}</li>)}</ul>
                    </details>
                  )}
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
