// SPDX-License-Identifier: AGPL-3.0-or-later
import { useState } from 'react'
import { authHeaders, can, useSession } from '../../api/session'

interface Proposal { scenario_id: string | null; scenario: string | null; params: Record<string, unknown>; camions_en_panne: number }
interface Turn { q: string; a: string; sources: string[]; tools: string[]; proposal: Proposal | null; ok: boolean }

const SUGGESTED = [
  'Pourquoi le point P009 est-il saturé ?',
  "Qu'est-ce qui change en saison des pluies ?",
  'Pourquoi ce signalement a-t-il 45/100 ?',
  'Quel paramètre pèse le plus sur les dépôts sauvages ?',
]

async function applyProposal(p: Proposal): Promise<string> {
  const h = { ...authHeaders(), 'Content-Type': 'application/json' }
  const created = await fetch('/api/scenarios', { method: 'POST', headers: h, body: JSON.stringify({ name: `Simulation proposée ${new Date().toLocaleTimeString('fr-FR')}`, parent_id: p.scenario_id }) }).then((r) => r.json())
  const patch: Record<string, unknown> = { params: p.params }
  if (p.camions_en_panne > 0) {
    const sc = await fetch(`/api/scenarios/${created.id}`, { headers: authHeaders() }).then((r) => r.json())
    patch.vehicles = (sc.vehicles ?? []).filter((v: { out_of_service: boolean }) => !v.out_of_service).slice(0, p.camions_en_panne).map((v: { id: string }) => ({ id: v.id, out_of_service: true }))
  }
  const r = await fetch(`/api/scenarios/${created.id}`, { method: 'PATCH', headers: h, body: JSON.stringify(patch) })
  return r.ok ? `Scénario « ${created.name} » créé : le plan se recalcule (page Scénario).` : `Refusé (${r.status})`
}

/** Module « Assistant » : panneau latéral pour les modérateurs et administrateurs connectés. Il lit et explique ;
 *  il ne change rien lui-même (une simulation proposée s'applique par un clic, via l'API normale). */
export function AssistantPanel() {
  const session = useSession()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [note, setNote] = useState<string | null>(null)
  if (!session || !can('moderateur', session)) return null

  async function ask(question: string) {
    setBusy(true)
    const t: Turn = { q: question, a: '', sources: [], tools: [], proposal: null, ok: true }
    setTurns((x) => [...x, t])
    try {
      const r = await fetch('/api/assistant/ask', { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) })
      if (!r.ok || !r.body) { const b = await r.json().catch(() => ({})); t.a = typeof b.detail === 'string' ? b.detail : `Erreur ${r.status}`; t.ok = false }
      else {
        const reader = r.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const lines = buf.split('\n'); buf = lines.pop() ?? ''
          for (const line of lines) {
            if (!line.trim()) continue
            const e = JSON.parse(line)
            if (e.type === 'outil') t.tools.push(e.nom)
            if (e.type === 'texte') t.a += e.texte
            if (e.type === 'fin') { t.sources = e.sources ?? []; t.proposal = e.proposition ?? null; t.ok = e.disponible !== false }
            setTurns((x) => [...x.slice(0, -1), { ...t }])
          }
        }
      }
    } catch { t.a = "Impossible de joindre l'assistant"; t.ok = false }
    setTurns((x) => [...x.slice(0, -1), { ...t }])
    setBusy(false)
  }

  return (
    <>
      <button className="btn primary" data-testid="assistant-open" style={{ position: 'fixed', right: 18, bottom: 18, zIndex: 50 }} onClick={() => setOpen(!open)}>Assistant</button>
      {open && (
        <aside data-testid="assistant-panel" style={{ position: 'fixed', right: 0, top: 0, bottom: 0, width: 'min(420px, 100vw)', background: '#fff', boxShadow: '-8px 0 24px rgba(0,0,0,.15)', zIndex: 49, display: 'flex', flexDirection: 'column', padding: 14, gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><b>Assistant (local, lecture seule)</b><button className="btn" onClick={() => setOpen(false)}>Fermer</button></div>
          <p className="muted">Il explique les plans, les simulations et les signalements à partir des données et des documents ; il ne modifie rien et ne juge pas un signalement.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SUGGESTED.map((s) => <button key={s} className="btn" disabled={busy} onClick={() => void ask(s)}>{s}</button>)}
          </div>
          <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {turns.map((t, i) => (
              <div key={i} className="card" style={{ padding: 10 }}>
                <b>{t.q}</b>
                <p style={{ whiteSpace: 'pre-wrap', color: t.ok ? undefined : '#b91c1c' }}>{t.a || '…'}</p>
                {t.tools.length > 0 && <p className="muted">Outils : {t.tools.join(', ')}</p>}
                {t.sources.length > 0 && <p className="muted">Sources : {t.sources.join(' · ')}</p>}
                {t.proposal && <button className="btn primary" onClick={() => void applyProposal(t.proposal!).then(setNote)}>Appliquer cette simulation</button>}
              </div>
            ))}
          </div>
          {note && <p className="muted" role="status">{note}</p>}
          <form onSubmit={(e) => { e.preventDefault(); if (q.trim().length >= 3) { void ask(q.trim()); setQ('') } }} style={{ display: 'flex', gap: 6 }}>
            <input aria-label="Question à l'assistant" style={{ flex: 1 }} value={q} maxLength={600} onChange={(e) => setQ(e.target.value)} placeholder="Votre question…" />
            <button className="btn primary" disabled={busy}>Demander</button>
          </form>
        </aside>
      )}
    </>
  )
}
