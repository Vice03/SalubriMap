// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, CheckCircle2, LocateFixed, MapPinned, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { accuracyLevel, useGps } from '../components/useGps'
import { preparePhoto } from '../components/photo'
import { outbox, uuid, type VolumeClass, type WasteType } from '../db'
import { VOLUME, WASTE } from '../labels'
import { notify, syncOutbox } from '../sync'

export function ReportPage({ onSent }: { onSent: () => void }) {
  const gps = useGps()
  const [manual, setManual] = useState(false)
  const [mLat, setMLat] = useState('12.371400')
  const [mLon, setMLon] = useState('-1.519700')
  const [photo, setPhoto] = useState<Blob | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [takenAt, setTakenAt] = useState<string | null>(null)
  const [waste, setWaste] = useState<WasteType | null>(null)
  const [volume, setVolume] = useState<VolumeClass>('wheelbarrow')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  useEffect(() => { if (gps.status === 'error') setManual(true) }, [gps.status])

  const pos = manual
    ? { lat: Number(mLat), lon: Number(mLon), accuracy: null }
    : gps.status === 'ok' ? gps.fix : null
  const posOk = pos != null && Number.isFinite(pos.lat) && Number.isFinite(pos.lon) && Math.abs(pos.lat) <= 90 && Math.abs(pos.lon) <= 180
  const ready = posOk && waste != null && !busy

  const submit = async () => {
    if (!ready || !pos) return
    setBusy(true)
    await outbox.put({
      clientId: uuid(), createdAt: takenAt ?? new Date().toISOString(), lat: pos.lat, lon: pos.lon,
      accuracy: pos.accuracy, wasteType: waste!, volumeClass: volume, comment: comment.trim(), photo,
      state: 'pending', attempts: 0,
    })
    notify()
    void syncOutbox()
    setBusy(false)
    setDone(true)
  }

  if (done) {
    return (
      <div className="done">
        <CheckCircle2 size={72} color="#16a34a" />
        <h2>Merci, c'est enregistré !</h2>
        <p>{navigator.onLine ? 'Votre signalement part vers la mairie.' : 'Pas de réseau : il partira tout seul dès que le réseau revient.'}</p>
        <button className="btn primary" onClick={onSent}>Voir mes signalements</button>
        <button className="btn ghost" onClick={() => { setDone(false); setPhoto(null); setPreview(null); setWaste(null); setComment(''); setTakenAt(null) }}>Signaler un autre dépotoir</button>
      </div>
    )
  }

  const acc = accuracyLevel(pos?.accuracy ?? null)
  return (
    <div className="page">
      <section className="card">
        <h3><span className="num">1</span>Photo du dépotoir</h3>
        <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={async (e) => {
          const f = e.target.files?.[0]
          if (!f) return
          setTakenAt(new Date().toISOString())
          setPhoto(await preparePhoto(f))
          setPreview(URL.createObjectURL(f))
        }} />
        <button className={`photo ${preview ? 'has' : ''}`} onClick={() => input.current?.click()}>
          {preview ? <img src={preview} alt="Photo du dépotoir" /> : <><Camera size={44} /><span>Prendre une photo</span></>}
        </button>
        {preview && <button className="link" onClick={() => input.current?.click()}>Reprendre la photo</button>}
      </section>

      <section className="card">
        <h3><span className="num">2</span>Position</h3>
        {!manual && gps.status === 'waiting' && <div className="gps wait"><LocateFixed size={18} className="spin" />Recherche du GPS…</div>}
        {!manual && gps.status === 'ok' && <div className="gps" style={{ color: acc.color, background: acc.bg }}><LocateFixed size={18} />{acc.label}</div>}
        {manual && (
          <>
            {gps.status === 'error' && <div className="gps" style={{ color: '#92400e', background: '#fef3c7' }}><MapPinned size={18} />{gps.message}</div>}
            <div className="row2">
              <label>Latitude<input inputMode="decimal" value={mLat} onChange={(e) => setMLat(e.target.value)} /></label>
              <label>Longitude<input inputMode="decimal" value={mLon} onChange={(e) => setMLon(e.target.value)} /></label>
            </div>
            <p className="hint">Saisie manuelle : la mairie vérifiera la position avant validation.</p>
          </>
        )}
        {gps.status === 'ok' && <button className="link" onClick={() => setManual(!manual)}>{manual ? 'Utiliser le GPS' : 'Saisir la position à la main'}</button>}
      </section>

      <section className="card">
        <h3><span className="num">3</span>Quel type de déchets ?</h3>
        <div className="grid3">
          {WASTE.map((w) => (
            <button key={w.k} className={`tile ${waste === w.k ? 'on' : ''}`} style={{ ['--c' as string]: w.color }} onClick={() => setWaste(w.k)}>
              <span className="emoji">{w.emoji}</span>{w.label}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h3><span className="num">4</span>Quelle quantité ?</h3>
        <div className="seg">
          {VOLUME.map((v) => (
            <button key={v.k} className={volume === v.k ? 'on' : ''} onClick={() => setVolume(v.k)}>{v.label}<small>{v.hint}</small></button>
          ))}
        </div>
        <textarea placeholder="Un détail utile ? (près du marché, bloque le caniveau…)" maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </section>

      <button className="btn primary big" disabled={!ready} onClick={() => void submit()}>
        <Send size={20} />{busy ? 'Enregistrement…' : 'Envoyer le signalement'}
      </button>
      {!ready && <p className="hint center">{!posOk ? 'Il manque la position.' : waste == null ? 'Choisissez le type de déchets.' : ''}{!photo && ' Une photo rend le signalement plus fiable.'}</p>}
    </div>
  )
}
