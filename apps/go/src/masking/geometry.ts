// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Masquage des visages et des plaques — décodage des sorties des deux modèles ONNX, sans dépendance au navigateur
 * (testé par Vitest). Mêmes formules que la référence Python (services/masking côté serveur).
 *   Visages : YuNet 2023mar (OpenCV Zoo, MIT), entrée 640×640 BGR 0–255, têtes par pas 8/16/32.
 *   Plaques : YOLOv9-t 384 « end2end » (open-image-models, MIT), entrée 384×384 RGB 0–1, NMS intégrée.
 */

export type Kind = 'visage' | 'plaque' | 'manuel'
export interface Box { x: number; y: number; w: number; h: number; kind: Kind; score: number; on: boolean }

export const FACE_SIZE = 640
export const PLATE_SIZE = 384
// Visages : seuil 0,5 et passe sur 2×2 tuiles au-delà de 1000 px (rappel 0,82 → 0,93 sur le jeu public de
// contrôle, docs/MASQUAGE.md) — identique au serveur (salubri_api/services/masking/detector.py).
export const FACE_THRESHOLD = 0.5
// Lot 2.1 (mesuré, docs/MASQUAGE.md) : image ramenée à WORK_MAX_SIDE px, puis tuiles carrées recouvrantes de 20 %
// de FACE_TILE px (visages) et PLATE_TILE px (plaques, score ≥ PLATE_TILE_THRESHOLD). Identique au serveur.
export const WORK_MAX_SIDE = 1280, FACE_TILE = 512, PLATE_TILE = 0 /* 0 : pas de tuiles pour les plaques (voir detector.py) */, TILE_OVERLAP = 0.2, PLATE_TILE_THRESHOLD = 0.85
/** Les tuiles cherchent les PETITS visages : plus haut qu'1/4 de tuile = faux positif probable (calandre, affiche). */
export const TILE_MAX_FACE = 0.25
export const PLATE_THRESHOLD = 0.25 // valeur par défaut d'open-image-models

/** Suppression des boîtes qui se recouvrent (IoU > seuil), la meilleure gardée. */
export function nms(boxes: Box[], iouMax: number): Box[] {
  const sorted = [...boxes].sort((a, b) => b.score - a.score)
  const keep: Box[] = []
  for (const b of sorted) {
    if (keep.every((k) => iou(k, b) <= iouMax)) keep.push(b)
  }
  return keep
}

export function iou(a: Box, b: Box): number {
  const x1 = Math.max(a.x, b.x), y1 = Math.max(a.y, b.y)
  const x2 = Math.min(a.x + a.w, b.x + b.w), y2 = Math.min(a.y + a.h, b.y + b.h)
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1)
  const union = a.w * a.h + b.w * b.h - inter
  return union > 0 ? inter / union : 0
}

/** Sorties YuNet → boîtes dans l'image d'origine. `ratio` = facteur appliqué pour tenir dans 640×640. */
export function decodeYunet(out: Record<string, { data: Float32Array | ArrayLike<number> }>, ratio: number, threshold = FACE_THRESHOLD): Box[] {
  const found: Box[] = []
  for (const s of [8, 16, 32]) {
    const n = FACE_SIZE / s
    const cls = out[`cls_${s}`].data, obj = out[`obj_${s}`].data, bb = out[`bbox_${s}`].data
    for (let i = 0; i < n * n; i++) {
      const score = Math.sqrt(Math.min(1, Math.max(0, cls[i])) * Math.min(1, Math.max(0, obj[i])))
      if (score < threshold) continue
      const r = Math.floor(i / n), c = i % n
      const cx = (c + bb[i * 4]) * s, cy = (r + bb[i * 4 + 1]) * s
      const w = Math.exp(bb[i * 4 + 2]) * s, h = Math.exp(bb[i * 4 + 3]) * s
      found.push({ x: (cx - w / 2) / ratio, y: (cy - h / 2) / ratio, w: w / ratio, h: h / ratio, kind: 'visage', score, on: true })
    }
  }
  return nms(found, 0.3)
}

/** Sortie YOLOv9 end2end [N, 7] = (lot, x1, y1, x2, y2, classe, score) → boîtes dans l'image d'origine. */
export function decodePlates(out: { data: Float32Array | ArrayLike<number>; dims: readonly number[] }, ratio: number, threshold = PLATE_THRESHOLD): Box[] {
  const rows = out.dims[0] ?? 0
  const found: Box[] = []
  for (let k = 0; k < rows; k++) {
    const o = k * 7
    const score = out.data[o + 6]
    if (score < threshold) continue
    const x1 = out.data[o + 1] / ratio, y1 = out.data[o + 2] / ratio
    found.push({ x: x1, y: y1, w: out.data[o + 3] / ratio - x1, h: out.data[o + 4] / ratio - y1, kind: 'plaque', score, on: true })
  }
  return found
}

/** Boîte agrandie d'une marge (fraction de la taille), bornée à l'image. */
export function withMargin(b: Box, width: number, height: number, margin = 0.2): { x: number; y: number; w: number; h: number } {
  const mx = b.w * margin, my = b.h * margin
  const x = Math.max(0, Math.floor(b.x - mx)), y = Math.max(0, Math.floor(b.y - my))
  const x2 = Math.min(width, Math.ceil(b.x + b.w + mx)), y2 = Math.min(height, Math.ceil(b.y + b.h + my))
  return { x, y, w: Math.max(0, x2 - x), h: Math.max(0, y2 - y) }
}

/** Tuiles carrées [x0, y0, x1, y1] de `size` px recouvrantes de 20 %, collées aux bords ; aucune si l'image tient
 * dans une tuile (à 5 % près). Même découpe que le serveur (salubri_api/services/masking/detector.py). */
export function tiles(width: number, height: number, size: number): [number, number, number, number][] {
  if (Math.max(width, height) <= size * 1.05) return []
  const step = size * (1 - TILE_OVERLAP)
  const starts = (n: number) => {
    if (n <= size) return [0]
    const k = Math.ceil((n - size) / step) + 1
    return Array.from({ length: k }, (_, i) => Math.trunc(Math.min(i * step, n - size)))
  }
  const out: [number, number, number, number][] = []
  for (const x of starts(width)) for (const y of starts(height)) out.push([x, y, Math.min(width, x + size), Math.min(height, y + size)])
  return out
}
