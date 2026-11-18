// SPDX-License-Identifier: AGPL-3.0-or-later
import { Bot, LogIn, Send, Sparkles, Wrench, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { askLogin, authHeaders, can, useSession } from '../../api/session'
import { ASK_EVENT } from './bus'

interface Proposal { scenario_id: string | null; scenario: string | null; params: Record<string, unknown>; camions_en_panne: number }
interface Turn { q: string; a: string; sources: string[]; tools: string[]; proposal: Proposal | null; ok: boolean; step?: string; waited?: number }
interface Status { disponible: boolean; modele: string }

const ANALYSES = [
  { label: 'Analyser la situation', q: 'Analyse la situation actuelle (dépotoirs, signalements, flotte, points saturés) et dis ce qui demande une action en priorité.' },
  { label: 'Comparer tous les cas', q: 'Compare tous les scénarios simulés et recommande le meilleur pour la mairie, avec les chiffres et les risques.' },
]
const SUGGESTED = [
  'Pourquoi le point P009 est-il saturé ?',
  "Qu'est-ce qui change en saison des pluies ?",
  'Pourquoi ce signalement a-t-il 45/100 ?',
  'Quel paramètre pèse le plus sur les dépôts sauvages ?',
]
const TOOL_LABEL: Record<string, string> = {
  resume_plan: 'plan', detail_point: 'point', diff_versions: 'versions', signalement: 'signalement', depotoirs_quartier: 'dépotoirs',
  parametres: 'paramètres', resultats_simulation: 'simulation', plan_arrondissement: 'plan d\'arrondissement',
  comparer_scenarios: 'comparaison des scénarios', etat_general: 'situation actuelle', proposer_simulation: 'proposition', points_saison: 'saisons',
}

async function applyProposal(p: Proposal): Promise<string> {
  const h = { ...authHeaders(), 'Content-Type': 'application/json' }
  const created = await fetch('/api/scenarios', { method: 'POST', headers: h, body: JSON.stringify({ name: `Simulation proposée ${new Date().toLocaleTimeString('fr-FR')}`, parent_id: p.scenario_id }) }).then((r) => r.json())
  const patch: Record<string, unknown> = { params: p.params }
  if (p.camions_en_panne > 0) {
    const sc = await fetch(`/api/scenarios/${created.id}`, { headers: authHeaders() }).then((r) => r.json())
    patch.vehicles = (sc.vehicles ?? []).filter((v: { out_of_service: boolean }) => !v.out_of_service).slice(0, p.camions_en_panne).map((v: { id: string }) => ({ id: v.id, out_of_service: true }))
  }
  const r = await fetch(`/api/scenarios/${created.id}`, { method: 'PATCH', headers: h, body: JSON.stringify(patch) })
  return r.ok ? `Scénario « ${created.name} » créé : le plan se recalcule (pages Scénario et Comparer).` : `Refusé (${r.status})`
}

/** Module « Assistant » : bulle de discussion. Visible de tous quand le module est allumé ; seuls les modérateurs et
 *  administrateurs connectés posent des questions. Il lit et explique ; il ne change rien lui-même (une simulation
 *  proposée s'applique par un clic, via l'API normale). */
export function AssistantPanel() {
  const session = useSession()
  const allowed = !!session && can('moderateur', session)
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [note, setNote] = useState<string | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [queued, setQueued] = useState<string | null>(null)
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    fetch('/api/assistant/status').then((r) => r.json()).then(setStatus).catch(() => setStatus({ disponible: false, modele: '?' }))
  }, [open])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [turns])
  // Une page demande une analyse (bouton « Analyser avec l'IA »)
  useEffect(() => {
    const on = (e: Event) => { setOpen(true); setQueued(String((e as CustomEvent).detail ?? '')) }
    window.addEventListener(ASK_EVENT, on)
    return () => window.removeEventListener(ASK_EVENT, on)
  }, [])
  useEffect(() => {
    if (!queued || busy) return
    if (!allowed) { void askLogin("L'assistant répond aux agents de la mairie connectés.") ; return }
    const x = queued; setQueued(null); void ask(x)
  }, [queued, allowed, busy])

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
            if (e.type === 'etape') t.step = e.texte
            if (e.type === 'attente') t.waited = (t.waited ?? 0) + 5
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
      {!open && (
        <button className="ai-fab" data-testid="assistant-open" onClick={() => setOpen(true)} aria-label="Ouvrir l'assistant IA">
          <span className="ai-fab-icon"><Bot size={22} /></span><span className="ai-fab-text">Assistant IA</span>
        </button>
      )}
      {open && (
        <aside className="ai-panel" data-testid="assistant-panel" aria-label="Assistant IA">
          <header className="ai-head">
            <span className="ai-avatar"><Sparkles size={18} /></span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <b>Assistant IA</b>
              <div className="ai-status">
                <span className={`dot ${status == null ? 'warn' : status.disponible ? 'ok' : 'bad'}`} />
                {status == null ? 'vérification…' : status.disponible ? `modèle local ${status.modele} · lecture seule` : 'modèle local injoignable · lecture seule'}
              </div>
            </div>
            <button className="ai-close" onClick={() => setOpen(false)} aria-label="Fermer"><X size={18} /></button>
          </header>

          <div className="ai-body">
            <div className="ai-msg bot">
              Bonjour ! J'analyse vos données (plans, simulations, signalements, paramètres) et j'explique les chiffres, avec mes sources.
              Je ne modifie rien (lecture seule) et je ne juge jamais un signalement.
              {status && !status.disponible && <div className="ai-warn">Aucun modèle de langue ne répond. Ouvrez l'application Ollama (ou LM Studio) sur ce PC : je la retrouve toute seule en quelques secondes, sans redémarrer Salubri. Pas de modèle installé : choix 12 du lanceur.</div>}
            </div>
            {!allowed && (
              <div className="ai-msg bot">
                Pour me poser une question, connectez-vous comme agent de la mairie (démonstration : <b>demo / ouaga2026</b>).
                <div><button className="ai-chip strong" onClick={() => void askLogin("L'assistant répond aux agents de la mairie connectés.")}><LogIn size={14} /> Se connecter</button></div>
              </div>
            )}
            {allowed && turns.length === 0 && (
              <div className="ai-suggest">
                {ANALYSES.map((s) => <button key={s.label} className="ai-chip strong" disabled={busy} onClick={() => void ask(s.q)}><Sparkles size={13} /> {s.label}</button>)}
                {SUGGESTED.map((s) => <button key={s} className="ai-chip" disabled={busy} onClick={() => void ask(s)}>{s}</button>)}
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} className="ai-turn">
                <div className="ai-msg me">{t.q}</div>
                <div className={`ai-msg bot${t.ok ? '' : ' err'}`}>
                  {t.tools.length > 0 && <div className="ai-tools"><Wrench size={12} /> a consulté : {[...new Set(t.tools)].map((x) => TOOL_LABEL[x] ?? x).join(', ')}</div>}
                  <div style={{ whiteSpace: 'pre-wrap' }}>{t.a || (busy && i === turns.length - 1 ? <span><span className="ai-typing"><i /><i /><i /></span> <small className="muted">{t.step ?? 'Le modèle se prépare…'}{t.waited ? ` (${t.waited} s — un modèle local sur processeur peut prendre 1 à 3 minutes)` : ''}</small></span> : '…')}</div>
                  {t.sources.length > 0 && <div className="ai-src">Sources : {t.sources.join(' · ')}</div>}
                  {t.proposal && <button className="ai-chip strong" onClick={() => void applyProposal(t.proposal!).then(setNote)}>Appliquer cette simulation</button>}
                </div>
              </div>
            ))}
            {note && <p className="muted" role="status">{note}</p>}
            <div ref={end} />
          </div>

          <form className="ai-input" onSubmit={(e) => { e.preventDefault(); if (allowed && q.trim().length >= 3) { void ask(q.trim()); setQ('') } }}>
            <input aria-label="Question à l'assistant" value={q} maxLength={600} disabled={!allowed} onChange={(e) => setQ(e.target.value)}
              placeholder={allowed ? 'Posez une question sur vos données…' : 'Connexion nécessaire'} />
            <button className="ai-send" disabled={busy || !allowed} aria-label="Envoyer"><Send size={16} /></button>
          </form>
        </aside>
      )}
    </>
  )
}
