// SPDX-License-Identifier: AGPL-3.0-or-later
import { pixelate } from './blur'
import type { Box } from './geometry'

/** Côté le plus long de la photo envoyée (le serveur réencode de toute façon à 2560 px au plus). */
export const MAX_SIDE = 2560

/** Image d'origine → JPEG masqué (sans EXIF : un canvas n'en écrit pas). L'original ne quitte jamais la mémoire. */
export async function renderMasked(src: ImageBitmap, boxes: Box[]): Promise<Blob> {
  const k = Math.min(1, MAX_SIDE / Math.max(src.width, src.height))
  const w = Math.round(src.width * k), h = Math.round(src.height * k)
  const c = document.createElement('canvas')
  c.width = w; c.height = h
  const g = c.getContext('2d', { willReadFrequently: true })!
  g.drawImage(src, 0, 0, w, h)
  const img = g.getImageData(0, 0, w, h)
  pixelate(img.data, w, h, boxes.map((b) => ({ ...b, x: b.x * k, y: b.y * k, w: b.w * k, h: b.h * k })))
  g.putImageData(img, 0, 0)
  return new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error('Encodage JPEG impossible'))), 'image/jpeg', 0.88))
}
