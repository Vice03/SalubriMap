// SPDX-License-Identifier: AGPL-3.0-or-later
import { withMargin, type Box } from './geometry'

/**
 * Masque irréversible : chaque zone (agrandie de 20 %) est réduite à une grille de 6 cases au plus sur son grand
 * côté, chaque case peinte de sa couleur moyenne. Il ne reste aucun pixel d'origine : un visage ou une plaque
 * tient dans quelques couleurs unies, qu'aucun « défloutage » ne peut reconstituer.
 * Travaille en place sur les octets RGBA d'un ImageData.
 */
export const CELLS = 6
export const MARGIN = 0.2

export function pixelate(data: Uint8ClampedArray, width: number, height: number, boxes: Box[], margin = MARGIN): number {
  let masked = 0
  for (const b of boxes) {
    if (!b.on) continue
    const r = withMargin(b, width, height, margin)
    if (r.w < 1 || r.h < 1) continue
    const cell = Math.max(2, Math.ceil(Math.max(r.w, r.h) / CELLS))
    for (let cy = r.y; cy < r.y + r.h; cy += cell) {
      for (let cx = r.x; cx < r.x + r.w; cx += cell) {
        const x2 = Math.min(cx + cell, r.x + r.w), y2 = Math.min(cy + cell, r.y + r.h)
        let sr = 0, sg = 0, sb = 0, n = 0
        for (let y = cy; y < y2; y++) for (let x = cx; x < x2; x++) {
          const i = (y * width + x) * 4
          sr += data[i]; sg += data[i + 1]; sb += data[i + 2]; n++
        }
        const R = Math.round(sr / n), G = Math.round(sg / n), B = Math.round(sb / n)
        for (let y = cy; y < y2; y++) for (let x = cx; x < x2; x++) {
          const i = (y * width + x) * 4
          data[i] = R; data[i + 1] = G; data[i + 2] = B
        }
      }
    }
    masked++
  }
  return masked
}
