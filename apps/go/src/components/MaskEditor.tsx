// SPDX-License-Identifier: AGPL-3.0-or-later
import { EyeOff, Loader2, Square, Undo2 } from 'lucide-react'
import { useEffect, useRef, useState, type PointerEvent } from 'react'
import type { Box } from '../masking/geometry'
import { renderMasked } from '../masking/render'

export interface Masked { blob: Blob; faces: number; plates: number; manual: number; ms: number | null }

const COLOR: Record<Box['kind'], string> = { visage: '#f28c28', plaque: '#2563eb', manuel: '#7c3aed' }

/**
 * Lot masquage : visages et plaques floutés automatiquement sur le téléphone, avant toute mise en file d'attente.
 * Toucher un cadre l'annule (faux positif) ; « Flouter une zone » permet d'en tracer un à la main.
 * Seule l'image masquée est remontée (onChange) ; l'original reste en mémoire et n'est jamais enregistré.
 */
export function MaskEditor({ source, onChange }: { source: Blob; onChange: (m: Masked | null) => void }) {
  const [bmp, setBmp] = useState<ImageBitmap | null>(null)
  const [boxes, setBoxes] = useState<Box[]>([])
  const [state, setState] = useState<'detecting' | 'ready' | 'manual-only'>('detecting')
  const [ms, setMs] = useState<number | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [draft, setDraft] = useState<Box | null>(null)
  const area = useRef<HTMLDivElement>(null)

  // 1. décodage + détection
  useEffect(() => {
    let alive = true
    onChange(null)
    setState('detecting'); setBoxes([]); setPreview(null)
    void (async () => {
      const b = await createImageBitmap(source, { imageOrientation: 'from-image' })
      if (!alive) return
      setBmp(b)
      try {
        // moteur ONNX chargé à la demande : l'écran d'accueil reste léger
        const { detect } = await import('../masking/detect')
        const d = await detect(b, b.width, b.height)
        if (!alive) return
        setBoxes(d.boxes); setMs(d.ms); setState('ready')
      } catch {
        if (alive) setState('manual-only') // modèles indisponibles : masquage manuel seulement, signalé à l'écran
      }
    })()
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source])

  // 2. rendu de l'image masquée à chaque changement de cadres
  useEffect(() => {
    if (!bmp || state === 'detecting') return
    let alive = true
    let url: string | null = null
    void renderMasked(bmp, boxes).then((blob) => {
      if (!alive) return
      url = URL.createObjectURL(blob)
      setPreview(url)
      const on = boxes.filter((b) => b.on)
      onChange({ blob, faces: on.filter((b) => b.kind === 'visage').length, plates: on.filter((b) => b.kind === 'plaque').length, manual: on.filter((b) => b.kind === 'manuel').length, ms })
    })
    return () => { alive = false; if (url) URL.revokeObjectURL(url) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bmp, boxes, state])

  const toImage = (e: PointerEvent) => {
    const r = area.current!.getBoundingClientRect()
    return { x: ((e.clientX - r.left) / r.width) * bmp!.width, y: ((e.clientY - r.top) / r.height) * bmp!.height }
  }
  const down = (e: PointerEvent) => {
    if (!drawing || !bmp) return
    const p = toImage(e)
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
    setDraft({ x: p.x, y: p.y, w: 0, h: 0, kind: 'manuel', score: 1, on: true })
  }
  const move = (e: PointerEvent) => {
    if (!draft) return
    const p = toImage(e)
    setDraft({ ...draft, w: p.x - draft.x, h: p.y - draft.y })
  }
  const up = () => {
    if (!draft || !bmp) return
    const b = { ...draft, x: Math.min(draft.x, draft.x + draft.w), y: Math.min(draft.y, draft.y + draft.h), w: Math.abs(draft.w), h: Math.abs(draft.h) }
    setDraft(null)
    if (b.w > bmp.width * 0.02 && b.h > bmp.height * 0.02) { setBoxes((bs) => [...bs, b]); setDrawing(false) }
  }
  const pct = (b: Box) => bmp && ({ left: `${(b.x / bmp.width) * 100}%`, top: `${(b.y / bmp.height) * 100}%`, width: `${(b.w / bmp.width) * 100}%`, height: `${(b.h / bmp.height) * 100}%` })
  const auto = boxes.filter((b) => b.kind !== 'manuel')
  const faces = auto.filter((b) => b.kind === 'visage' && b.on).length
  const plates = auto.filter((b) => b.kind === 'plaque' && b.on).length

  return (
    <div className="mask-editor">
      <div ref={area} className={`mask-area ${drawing ? 'drawing' : ''}`} onPointerDown={down} onPointerMove={move} onPointerUp={up}>
        {preview ? <img src={preview} alt="Photo du dépotoir, visages et plaques floutés" draggable={false} /> : <div className="mask-wait"><Loader2 className="spin" size={28} />Masquage des visages et des plaques…</div>}
        {preview && boxes.map((b, i) => (
          <button key={i} type="button" className={`mask-box ${b.on ? '' : 'off'}`} style={{ ...pct(b), borderColor: COLOR[b.kind] }}
            aria-pressed={b.on} aria-label={`${b.kind} ${b.on ? 'flouté — toucher pour annuler' : 'non flouté — toucher pour flouter'}`}
            onClick={(e) => { e.stopPropagation(); if (!drawing) setBoxes((bs) => bs.map((x, j) => (j === i ? { ...x, on: !x.on } : x))) }}>
            <span style={{ background: COLOR[b.kind] }}>{b.kind}</span>
          </button>
        ))}
        {draft && <div className="mask-box draft" style={{ ...pct({ ...draft, x: Math.min(draft.x, draft.x + draft.w), y: Math.min(draft.y, draft.y + draft.h), w: Math.abs(draft.w), h: Math.abs(draft.h) }) }} />}
      </div>
      <p className="mask-status" role="status" data-ms={ms ?? undefined}>
        {state === 'detecting' && 'Recherche des visages et des plaques sur le téléphone…'}
        {state === 'ready' && (faces + plates > 0
          ? <><EyeOff size={15} /> {faces} visage(s) et {plates} plaque(s) floutés automatiquement. Touchez un cadre pour l'annuler.</>
          : <><EyeOff size={15} /> Aucun visage ni plaque détecté. Si vous en voyez un, floutez-le à la main.</>)}
        {state === 'manual-only' && 'Détection automatique indisponible sur ce téléphone : floutez à la main les visages et les plaques.'}
      </p>
      <div className="mask-actions">
        <button type="button" className={`btn ${drawing ? 'primary' : 'ghost'} small`} disabled={!preview} onClick={() => setDrawing((d) => !d)}>
          <Square size={16} />{drawing ? 'Tracez la zone sur la photo' : 'Flouter une zone'}
        </button>
        {boxes.some((b) => b.kind === 'manuel') && (
          <button type="button" className="btn ghost small" onClick={() => setBoxes((bs) => { const i = bs.map((b) => b.kind).lastIndexOf('manuel'); return bs.filter((_, j) => j !== i) })}>
            <Undo2 size={16} />Retirer la dernière zone
          </button>
        )}
      </div>
    </div>
  )
}
