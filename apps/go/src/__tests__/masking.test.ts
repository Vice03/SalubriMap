// SPDX-License-Identifier: AGPL-3.0-or-later
/** Lot masquage : pixellisation irréversible, décodage des deux modèles, date EXIF. */
import { describe, expect, it } from 'vitest'
import { CELLS, pixelate } from '../masking/blur'
import { exifDate } from '../masking/exif'
import { decodePlates, decodeYunet, iou, nms, withMargin, type Box } from '../masking/geometry'

function noise(w: number, h: number, seed = 7): Uint8ClampedArray {
  const d = new Uint8ClampedArray(w * h * 4)
  let s = seed
  for (let i = 0; i < d.length; i++) { s = (s * 1103515245 + 12345) & 0x7fffffff; d[i] = i % 4 === 3 ? 255 : s % 256 }
  return d
}
const box = (x: number, y: number, w: number, h: number, extra: Partial<Box> = {}): Box => ({ x, y, w, h, kind: 'visage', score: 0.9, on: true, ...extra })

describe('pixellisation', () => {
  it('ne laisse aucun pixel d origine dans la zone (marge comprise) et ne touche pas au reste', () => {
    const w = 200, h = 160
    const orig = noise(w, h)
    const img = new Uint8ClampedArray(orig)
    expect(pixelate(img, w, h, [box(60, 40, 50, 60)])).toBe(1)
    const r = withMargin(box(60, 40, 50, 60), w, h)
    const colors = new Set<string>()
    let same = 0, n = 0
    for (let y = r.y; y < r.y + r.h; y++) for (let x = r.x; x < r.x + r.w; x++) {
      const i = (y * w + x) * 4
      colors.add(`${img[i]},${img[i + 1]},${img[i + 2]}`)
      if (img[i] === orig[i] && img[i + 1] === orig[i + 1] && img[i + 2] === orig[i + 2]) same++
      n++
    }
    expect(colors.size).toBeLessThanOrEqual(CELLS * CELLS) // quelques aplats, plus aucun détail
    expect(same / n).toBeLessThan(0.001) // sur du bruit, aucun pixel ne reste par hasard
    // hors zone : intact
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) continue
      const i = (y * w + x) * 4
      expect(img[i]).toBe(orig[i])
    }
  })

  it('une boîte annulée (faux positif) n est pas floutée ; une boîte au bord est bornée à l image', () => {
    const w = 64, h = 64, orig = noise(w, h, 3), img = new Uint8ClampedArray(orig)
    expect(pixelate(img, w, h, [box(10, 10, 20, 20, { on: false })])).toBe(0)
    expect(Array.from(img)).toEqual(Array.from(orig))
    expect(pixelate(img, w, h, [box(50, 50, 40, 40)])).toBe(1)
    expect(withMargin(box(50, 50, 40, 40), w, h)).toEqual({ x: 42, y: 42, w: 22, h: 22 })
  })
})

describe('décodage', () => {
  it('YuNet : une cellule au-dessus du seuil donne une boîte à l échelle de l image', () => {
    const t = (n: number, k: number) => ({ data: new Float32Array(n * k) })
    const out: Record<string, { data: Float32Array }> = {}
    for (const s of [8, 16, 32]) {
      const n = (640 / s) ** 2
      out[`cls_${s}`] = t(n, 1); out[`obj_${s}`] = t(n, 1); out[`bbox_${s}`] = t(n, 4); out[`kps_${s}`] = t(n, 10)
    }
    // pas 32 : cellule (ligne 3, colonne 5), score 0,9×0,9 → 0,9 ; taille e^1 × 32
    const i = 3 * 20 + 5
    out.cls_32.data[i] = 0.9; out.obj_32.data[i] = 0.9
    out.bbox_32.data.set([0.5, 0.5, 1, 1], i * 4)
    const [b] = decodeYunet(out, 0.5) // image deux fois plus grande que 640
    const side = Math.exp(1) * 32
    expect(b.score).toBeCloseTo(0.9, 5)
    expect(b.x).toBeCloseTo(((5.5) * 32 - side / 2) / 0.5, 3)
    expect(b.w).toBeCloseTo(side / 0.5, 3)
    expect(decodeYunet(out, 0.5, 0.95)).toHaveLength(0)
  })

  it('plaques : lignes (lot, x1, y1, x2, y2, classe, score), seuil appliqué', () => {
    const data = new Float32Array([0, 10, 20, 50, 30, 0, 0.8, 0, 100, 100, 120, 110, 0, 0.1])
    const boxes = decodePlates({ data, dims: [2, 7] }, 0.5)
    expect(boxes).toHaveLength(1)
    expect(boxes[0]).toMatchObject({ x: 20, y: 40, w: 80, h: 20, kind: 'plaque' })
  })

  it('NMS garde la meilleure de deux boîtes qui se recouvrent', () => {
    const a = box(0, 0, 10, 10, { score: 0.9 }), b = box(1, 1, 10, 10, { score: 0.8 }), c = box(50, 50, 10, 10, { score: 0.7 })
    expect(iou(a, b)).toBeGreaterThan(0.6)
    expect(nms([b, a, c], 0.3)).toEqual([a, c])
  })
})

describe('EXIF', () => {
  it('date EXIF → ISO local sans fuseau, comme la lecture serveur', () => {
    expect(exifDate('2026:11:17 08:05:09')).toBe('2026-11-17T08:05:09')
    expect(exifDate('n importe quoi')).toBeNull()
    expect(exifDate(undefined)).toBeNull()
  })
})
