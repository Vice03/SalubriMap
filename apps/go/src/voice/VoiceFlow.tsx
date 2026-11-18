// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, CheckCircle2, MapPin, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useGps } from '../components/useGps'
import { MaskEditor, type Masked } from '../components/MaskEditor'
import { outbox, uuid, type VolumeClass, type WasteType } from '../db'
import { VOLUME, WASTE } from '../labels'
import { readExif, type ExifFields } from '../masking/exif'
import { notify, syncOutbox } from '../sync'
import { playCue } from './player'
import { locAsk, locDenied, locWait, photoAsk, photoContinue, qtyCues, thanksCues, typeCues, type Cue, type Lang } from './script'
import { useCues } from './useCues'

type Step = 'photo' | 'qty' | 'type' | 'loc' | 'thanks'
const ETAPES: { k: Step; icon: string }[] = [{ k: 'photo', icon: '📷' }, { k: 'qty', icon: '🧺' }, { k: 'type', icon: '🗑️' }, { k: 'loc', icon: '📍' }]
const none: Cue[] = []

/** Signalement guidé par la voix : photo, quantité, type, localisation, merci. Un seul grand bouton qui brille par étape. */
export function VoiceFlow({ lang, onSent, onAgain, onClassic }: { lang: Lang; onSent: () => void; onAgain: () => void; onClassic: () => void }) {
  const [step, setStep] = useState<Step>('photo')
  const [source, setSource] = useState<Blob | null>(null)
  const [masked, setMasked] = useState<Masked | null>(null)
  const [, setMaskPending] = useState<string | null>(null)
  const [exif, setExif] = useState<ExifFields | null>(null)
  const [takenAt, setTakenAt] = useState<string | null>(null)
  const [volume, setVolume] = useState<VolumeClass | null>(null)
  const [waste, setWaste] = useState<WasteType | null>(null)
  const [gpsOn, setGpsOn] = useState(false)
  const [online, setOnline] = useState(true)
  const sent = useRef(false)
  const input = useRef<HTMLInputElement>(null)
  const gps = useGps(gpsOn)
  const masking = source != null && masked == null

  // la voix de chaque étape ; `glow` = ce qui brille pendant qu'elle parle
  const cues = step === 'photo' ? (source ? (masked ? photoContinue : none) : photoAsk)
    : step === 'qty' ? qtyCues
    : step === 'type' ? typeCues
    : step === 'loc' ? (!gpsOn ? locAsk : gps.status === 'waiting' ? locWait : gps.status === 'error' ? locDenied : none)
    : thanksCues(online)
  const { glow, blocked, replay, stop } = useCues(lang, cues, { repeat: step === 'qty' || step === 'type' ? 3 : 2, pauseMs: 6000 })

  // localisation déjà autorisée : pas besoin de la redemander
  useEffect(() => {
    if (step !== 'loc' || gpsOn) return
    void navigator.permissions?.query({ name: 'geolocation' }).then((p) => { if (p.state === 'granted') setGpsOn(true) }).catch(() => {})
  }, [step, gpsOn])

  // position trouvée : on enregistre tout de suite
  useEffect(() => {
    if (step !== 'loc' || gps.status !== 'ok' || sent.current) return
    sent.current = true
    const fix = gps.fix
    void (async () => {
      const clientId = uuid()
      await outbox.put({
        clientId, createdAt: takenAt ?? new Date().toISOString(), lat: fix.lat, lon: fix.lon, accuracy: fix.accuracy,
        wasteType: waste ?? 'mixed', volumeClass: volume ?? 'wheelbarrow', photo: masked?.blob ?? null,
        exif: masked?.blob ? exif ?? undefined : undefined,
        masking: masked ? { faces: masked.faces, plates: masked.plates, manual: masked.manual, mode: masked.mode } : undefined,
        comment: '', state: 'pending', attempts: 0,
      })
      notify()
      // « transmis » seulement si le serveur a vraiment répondu (6 s au plus) ; sinon « enregistré, sera transmis »
      await Promise.race([syncOutbox().catch(() => 0), new Promise((res) => window.setTimeout(res, 6000))])
      setOnline((await outbox.all()).some((i) => i.clientId === clientId && i.state === 'sent'))
      setStep('thanks')
    })()
  }, [step, gps, takenAt, waste, volume, masked, exif])

  const choose = async (apply: () => void, id: string, next: Step) => {
    stop()
    apply()
    await playCue(lang, id, 500) // la voix répète le choix : le citoyen entend ce qu'il a touché
    setStep(next)
  }
  const retryGps = () => { setGpsOn(false); window.setTimeout(() => setGpsOn(true), 80) }
  const i = ETAPES.findIndex((e) => e.k === step)

  return (
    <div className="page vg-flow">
      {step !== 'thanks' && (
        <ol className="vg-dots" aria-label="Étapes">
          {ETAPES.map((e, n) => <li key={e.k} className={n < i ? 'is-done' : n === i ? 'is-now' : ''}><span aria-hidden>{n < i ? '✓' : e.icon}</span></li>)}
        </ol>
      )}
      {step !== 'thanks' && <button className="icon vg-replay" aria-label="Réécouter" onClick={replay}><Volume2 size={22} /></button>}
      {blocked && <p className="vg-unlock" role="status"><Volume2 size={22} />Touchez l'écran pour entendre la voix</p>}

      {step === 'photo' && (
        <section className="card vg-card">
          <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={async (e) => {
            const f = e.target.files?.[0]
            if (!f) return
            stop()
            setTakenAt(new Date().toISOString())
            setMasked(null)
            setExif(await readExif(f)) // avant masquage : le JPEG masqué n'aura plus d'EXIF
            setSource(f)
            e.target.value = ''
          }} />
          {!source && (
            <button className={`vg-camera glow ${glow === 'camera' ? 'glow-on' : ''}`} onClick={() => { stop(); input.current?.click() }}>
              <Camera size={84} /><span>Photo</span>
            </button>
          )}
          {source && <MaskEditor source={source} onChange={setMasked} onPending={setMaskPending} />}
          {source && (
            <>
              <button className={`btn primary big vg-go glow ${glow === 'continue' ? 'glow-on' : ''}`} disabled={masking} onClick={() => { stop(); setStep('qty') }}>
                <CheckCircle2 size={30} />OK
              </button>
              <button className="link" onClick={() => { stop(); input.current?.click() }}>Reprendre la photo</button>
            </>
          )}
          {!source && <button className="link" onClick={() => { stop(); setStep('qty') }}>Passer sans photo</button>}
        </section>
      )}

      {step === 'qty' && (
        <section className="card vg-card">
          <div className="vg-grid">
            {VOLUME.map((v) => (
              <button key={v.k} className={`vg-opt glow ${glow === v.k ? 'glow-on' : ''} ${volume === v.k ? 'on' : ''}`} aria-label={v.label}
                onClick={() => void choose(() => setVolume(v.k), `qty_${v.k}`, 'type')}>
                <span className="vg-emoji" aria-hidden>{v.emoji}</span><span>{v.label}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 'type' && (
        <section className="card vg-card">
          <div className="vg-grid">
            {WASTE.map((w) => (
              <button key={w.k} className={`vg-opt glow ${glow === w.k ? 'glow-on' : ''} ${waste === w.k ? 'on' : ''}`} style={{ ['--c' as string]: w.color }} aria-label={w.label}
                onClick={() => void choose(() => setWaste(w.k), `type_${w.k}`, 'loc')}>
                <span className="vg-emoji" aria-hidden>{w.emoji}</span><span>{w.label}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 'loc' && (
        <section className="card vg-card">
          {gpsOn && gps.status === 'waiting' && <p className="vg-wait" role="status"><MapPin size={64} className="spin" /></p>}
          {(!gpsOn || gps.status === 'error') && (
            <button className={`vg-camera glow ${glow === 'loc' ? 'glow-on' : ''}`} onClick={() => { stop(); if (gpsOn) retryGps(); else setGpsOn(true) }}>
              <MapPin size={84} /><span>{gps.status === 'error' && gpsOn ? 'Réessayer' : 'Position'}</span>
            </button>
          )}
          {gps.status === 'error' && gpsOn && <p className="hint center">{gps.message}</p>}
          <button className="link" onClick={() => { stop(); onClassic() }}>Écrire à la main</button>
        </section>
      )}

      {step === 'thanks' && (
        <section className="done">
          <CheckCircle2 size={96} color="#16a34a" />
          <button className={`btn primary big vg-go glow ${glow === 'again' ? 'glow-on' : ''}`} onClick={() => { stop(); onAgain() }}><Camera size={28} />+</button>
          <button className="link" onClick={() => { stop(); onSent() }}>Voir mes signalements</button>
        </section>
      )}
    </div>
  )
}
