// SPDX-License-Identifier: AGPL-3.0-or-later
import { CheckCircle2, Server, XCircle } from 'lucide-react'
import { useState } from 'react'
import { estReseauLocal, getServer, normalizeServer, setServer } from '../server'

/** Écran affiché seulement dans l'application Android : adresse du serveur Salubri (ordinateur du réseau local). */
export function ServerSetup({ onSaved, onCancel }: { onSaved: () => void; onCancel?: () => void }) {
  const [addr, setAddr] = useState(getServer().replace(/^http:\/\//, ''))
  const [state, setState] = useState<'idle' | 'testing' | 'ok' | 'ko'>('idle')
  const [msg, setMsg] = useState('')

  async function test() {
    const base = normalizeServer(addr)
    if (!base) { setState('ko'); setMsg('Saisissez une adresse, par exemple 192.168.1.20'); return }
    if (!estReseauLocal(base)) { setState('ko'); setMsg('Adresse non autorisée : utilisez l\'adresse locale de l\'ordinateur (10.x, 172.16-31.x ou 192.168.x)'); return }
    setState('testing'); setMsg('')
    try {
      const r = await Promise.race([
        fetch(`${base}/api/health`),
        new Promise<never>((_, rej) => setTimeout(() => rej(new Error('delai')), 8000)),
      ])
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setState('ok'); setMsg('Serveur Salubri joignable')
    } catch (e) {
      setState('ko'); setMsg(`Serveur injoignable (${(e as Error).message}). Même Wi-Fi que l'ordinateur ? Pare-feu ouvert ?`)
    }
  }

  return (
    <div className="app">
      <main style={{ paddingBottom: 24 }}>
        <div className="card" style={{ marginTop: 24 }}>
          <h3><Server size={20} />Adresse du serveur Salubri</h3>
          <input value={addr} inputMode="url" autoCapitalize="none" autoCorrect="off" placeholder="192.168.1.20"
            onChange={(e) => { setAddr(e.target.value); setState('idle') }} aria-label="Adresse du serveur Salubri" />
          <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
            <button className="btn ghost" onClick={() => void test()} disabled={state === 'testing'}>{state === 'testing' ? 'Test…' : 'Tester'}</button>
            <button className="btn primary" onClick={() => { setServer(normalizeServer(addr)); onSaved() }} disabled={!estReseauLocal(normalizeServer(addr))}>Enregistrer</button>
          </div>
          {state === 'ok' && <p style={{ color: '#15803d', display: 'flex', gap: 6, alignItems: 'center' }}><CheckCircle2 size={18} />{msg}</p>}
          {state === 'ko' && <p style={{ color: '#dc2626', display: 'flex', gap: 6, alignItems: 'center' }}><XCircle size={18} />{msg}</p>}
          {onCancel && <p><a href="#" onClick={(e) => { e.preventDefault(); onCancel() }}>Annuler</a></p>}
        </div>
      </main>
    </div>
  )
}
