// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, LocateFixed, Send } from 'lucide-react'
import { useRef, useState } from 'react'
import { accuracyLevel, useGps } from '../../components/useGps'
import { MaskEditor, type Masked } from '../../components/MaskEditor'
import { deviceId } from '../../db'

/** Module « Saisons » : signaler une route impraticable (photo masquée comme un signalement de dépotoir).
 *  La mairie vérifie avant d'en tenir compte dans les tournées. Envoi direct : il faut du réseau. */
export function RoadReportPage() {
  const gps = useGps()
  const input = useRef<HTMLInputElement>(null)
  const [source, setSource] = useState<Blob | null>(null)
  const [masked, setMasked] = useState<Masked | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pos = gps.status === 'ok' ? gps.fix : null
  const acc = accuracyLevel(pos?.accuracy ?? null)
  const ready = pos != null && !busy && !(source && !masked)

  async function send() {
    if (!pos) return
    setBusy(true)
    setMsg(null)
    const f = new FormData()
    f.append('lat', pos.lat.toFixed(7))
    f.append('lon', pos.lon.toFixed(7))
    if (pos.accuracy != null) f.append('accuracy', String(Math.round(pos.accuracy)))
    f.append('period', 'rain')
    if (comment) f.append('comment', comment.slice(0, 900))
    f.append('device_id', await deviceId())
    f.append('client_id', crypto.randomUUID())
    if (masked) {
      f.append('photo', masked.blob, 'photo.jpg')
      f.append('masking_client', JSON.stringify({ faces: masked.faces, plates: masked.plates, manual: masked.manual, mode: masked.mode }))
    }
    try {
      const r = await fetch('/api/roads/reports', { method: 'POST', body: f })
      const b = await r.json().catch(() => ({}))
      setMsg(r.ok ? 'Merci : la mairie va vérifier cette route avant de changer les tournées.' : `Refusé : ${typeof b.detail === 'string' ? b.detail : r.status}`)
      if (r.ok) { setSource(null); setMasked(null); setComment('') }
    } catch {
      setMsg('Pas de réseau : réessayez quand le réseau revient.')
    } finally { setBusy(false) }
  }

  return (
    <div className="page with-sticky">
      <section className="card">
        <h3><span className="num">1</span>Route impraticable</h3>
        <p className="hint">Route inondée, effondrée ou bloquée : les camions et les habitants ne passent plus.</p>
        <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) { setMasked(null); setSource(file) }
          e.target.value = ''
        }} />
        {source
          ? <MaskEditor source={source} onChange={setMasked} onPending={setPending} />
          : <button className="photo" onClick={() => input.current?.click()}><Camera size={44} /><span>Photo de la route</span></button>}
      </section>
      <section className="card">
        <h3><span className="num">2</span>Position</h3>
        {gps.status === 'waiting' && <div className="gps wait"><LocateFixed size={18} className="spin" />Recherche du GPS…</div>}
        {gps.status === 'ok' && <div className="gps" style={{ color: acc.color, background: acc.bg }}><LocateFixed size={18} />{acc.label}</div>}
        {gps.status === 'error' && <div className="gps">{gps.message}</div>}
        <textarea placeholder="Un détail utile ? (eau jusqu'aux genoux, radier coupé…)" maxLength={900} value={comment} onChange={(e) => setComment(e.target.value)} />
      </section>
      <div className="sticky-send">
        {msg && <p className="hint center" role="status">{msg}</p>}
        {source && !masked && <p className="hint center">{pending ?? 'Masquage des visages et des plaques en cours…'}</p>}
        <button className="btn primary big" disabled={!ready} onClick={() => void send()}><Send size={20} />{busy ? 'Envoi…' : 'Signaler la route'}</button>
      </div>
    </div>
  )
}
