// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, CheckCircle2, LocateFixed, MapPinned, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { accuracyLevel, useGps } from '../components/useGps'
import { MaskEditor, type Masked } from '../components/MaskEditor'
import { outbox, uuid, type VolumeClass, type WasteType } from '../db'
import { readExif, type ExifFields } from '../masking/exif'
import { VOLUME, WASTE } from '../labels'
import { notify, syncOutbox } from '../sync'

export function ReportPage({ onSent }: { onSent: () => void }) {
  const gps = useGps()
  const [manual, setManual] = useState(false)
  const [mLat, setMLat] = useState('')
  const [mLon, setMLon] = useState('')
  // lot masquage : `source` (photo d'origine) reste en mémoire ; seule `masked` (floutée) entre dans la file
  const [source, setSource] = useState<Blob | null>(null)
  const [masked, setMasked] = useState<Masked | null>(null)
  const [maskPending, setMaskPending] = useState<string | null>(null) // mode manuel : confirmation attendue
  const [exif, setExif] = useState<ExifFields | null>(null)
  const [takenAt, setTakenAt] = useState<string | null>(null)
  const photo = masked?.blob ?? null
  const [waste, setWaste] = useState<WasteType | null>(null)
  const [volume, setVolume] = useState<VolumeClass>('wheelbarrow')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => { if (gps.status === 'error') setManual(true) }, [gps.status])

  const pos = manual
    ? { lat: Number(mLat), lon: Number(mLon), accuracy: null }
    : gps.status === 'ok' ? gps.fix : null
  const posOk = pos != null && (!manual || (mLat.trim() !== '' && mLon.trim() !== '')) && Number.isFinite(pos.lat) && Number.isFinite(pos.lon) && Math.abs(pos.lat) <= 90 && Math.abs(pos.lon) <= 180
  const masking = source != null && masked == null // la photo choisie n'est pas encore masquée
  const ready = posOk && waste != null && !busy && !masking

  const submit = async () => {
    if (!ready || !pos) return
    setBusy(true)
    await outbox.put({
      clientId: uuid(), createdAt: takenAt ?? new Date().toISOString(), lat: pos.lat, lon: pos.lon,
      accuracy: pos.accuracy, wasteType: waste!, volumeClass: volume, photo,
      exif: photo ? exif ?? undefined : undefined,
      masking: masked ? { faces: masked.faces, plates: masked.plates, manual: masked.manual, mode: masked.mode } : undefined,
      comment: (manual ? `[Position saisie à la main] ${comment.trim()}` : comment.trim()).trim(),
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
        <button className="btn ghost" onClick={() => { setDone(false); setSource(null); setMasked(null); setExif(null); setWaste(null); setComment(''); setTakenAt(null) }}>Signaler un autre dépotoir</button>
      </div>
    )
  }

  const acc = accuracyLevel(pos?.accuracy ?? null)
  const stepDone = [photo != null, posOk, waste != null, true]
  const why = masking ? (maskPending ?? 'Masquage des visages et des plaques en cours…') : !posOk ? 'Il manque la position (étape 2).' : waste == null ? 'Choisissez le type de déchets (étape 3).' : ''
  return (
    <div className="page with-sticky">
      <ol className="steps" aria-label="Étapes du signalement">
        {['Photo', 'Position', 'Type', 'Quantité'].map((s, n) => (
          <li key={s} className={stepDone[n] ? 'is-done' : ''}><span>{stepDone[n] ? '✓' : n + 1}</span>{s}</li>
        ))}
      </ol>
      <section className="card">
        <h3><span className="num">1</span>Photo du dépotoir</h3>
        <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={async (e) => {
          const f = e.target.files?.[0]
          if (!f) return
          setTakenAt(new Date().toISOString())
          setMasked(null)
          setExif(await readExif(f)) // avant masquage : le JPEG masqué n'aura plus d'EXIF
          setSource(f)
          e.target.value = ''
        }} />
        {source
          ? <MaskEditor source={source} onChange={setMasked} onPending={setMaskPending} />
          : <button className="photo" onClick={() => input.current?.click()}><Camera size={44} /><span>Prendre une photo</span></button>}
        {source && <button className="link" onClick={() => input.current?.click()}>Reprendre la photo</button>}
      </section>

      <section className="card">
        <h3><span className="num">2</span>Position</h3>
        {!manual && gps.status === 'waiting' && <div className="gps wait"><LocateFixed size={18} className="spin" />Recherche du GPS…</div>}
        {!manual && gps.status === 'ok' && <div className="gps" style={{ color: acc.color, background: acc.bg }}><LocateFixed size={18} />{acc.label}</div>}
        {manual && (
          <>
            {gps.status === 'error' && <div className="gps" style={{ color: '#92400e', background: '#fef3c7' }}><MapPinned size={18} />{gps.message}</div>}
            <div className="row2">
              <label>Latitude<input inputMode="decimal" placeholder="ex. 12.37142" value={mLat} onChange={(e) => setMLat(e.target.value.replace(',', '.'))} /></label>
              <label>Longitude<input inputMode="decimal" placeholder="ex. -1.51970" value={mLon} onChange={(e) => setMLon(e.target.value.replace(',', '.'))} /></label>
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
            <button key={w.k} className={`tile ${waste === w.k ? 'on' : ''}`} style={{ ['--c' as string]: w.color }} aria-pressed={waste === w.k} onClick={() => setWaste(w.k)}>
              <span className="emoji">{w.emoji}</span>{w.label}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h3><span className="num">4</span>Quelle quantité ?</h3>
        <div className="seg">
          {VOLUME.map((v) => (
            <button key={v.k} className={volume === v.k ? 'on' : ''} title={v.hint} aria-pressed={volume === v.k} onClick={() => setVolume(v.k)}>
              <span className="emoji" aria-hidden>{v.emoji}</span>{v.label}
            </button>
          ))}
        </div>
        <textarea placeholder="Un détail utile ? (près du marché, bloque le caniveau…)" maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </section>

      <div className="sticky-send">
        {(!ready || !photo) && <p className="hint center" role="status">{why}{!photo && ' Une photo rend le signalement plus fiable.'}</p>}
        <button className="btn primary big" disabled={!ready} onClick={() => void submit()}>
          <Send size={20} />{busy ? 'Enregistrement…' : 'Envoyer le signalement'}
        </button>
      </div>
    </div>
  )
}
