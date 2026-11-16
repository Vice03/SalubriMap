// SPDX-License-Identifier: AGPL-3.0-or-later
import { Loader2 } from 'lucide-react'
import { EVENT, STAGES } from '../../lib/labels'
import { useApp } from '../../state/app'

export function Toasts() {
  const { toasts } = useApp()
  return <div className="toasts" aria-live="polite">{toasts.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>)}</div>
}

export function PipelineProgress() {
  const { tracking } = useApp()
  if (!tracking) return null
  const ran = Object.values(tracking.stages).filter((s) => !s.cache_hit && !s.running).length
  const hit = Object.values(tracking.stages).filter((s) => s.cache_hit).length
  return (
    <div className="progress" role="status">
      <div className="progress-head">
        {!tracking.done && <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} />}
        <span>{tracking.failed ? 'Recalcul échoué' : tracking.done ? 'Plan recalculé' : 'Recalcul du plan en cours'} — {EVENT[tracking.label] ?? tracking.label}</span>
        <span className="muted" style={{ marginLeft: 'auto' }}>
          {ran} recalculée(s) · {hit} réutilisée(s){tracking.totalMs ? ` · ${(tracking.totalMs / 1000).toFixed(1).replace('.', ',')} s` : ''}
        </span>
      </div>
      <div className="stages">
        {STAGES.map((s) => {
          const st = tracking.stages[s.code]
          const cls = !st ? '' : st.running ? 'run' : st.cache_hit ? 'hit' : 'done'
          return (
            <div key={s.code} className={`stage ${cls}`}>
              <b>{s.code} · {s.name}</b>
              {st && !st.running ? (st.cache_hit ? 'réutilisé' : `${st.duration_ms} ms`) : st?.running ? 'en cours…' : 'en attente'}
            </div>
          )
        })}
      </div>
      {tracking.failed && <div style={{ color: '#b91c1c', marginTop: 8, fontSize: 13 }}>{tracking.failed} — l'ancien plan reste affiché.</div>}
    </div>
  )
}
