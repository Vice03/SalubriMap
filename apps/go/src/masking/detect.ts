// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Détection hors ligne des visages et des plaques sur le téléphone (onnxruntime-web, WebAssembly, un fil).
 * Modèles et moteur (émis par Vite dans assets/) sont servis par l'application et mis en cache par le service worker : aucun réseau à l'usage.
 */
import * as ort from 'onnxruntime-web/wasm'
import { decodePlates, decodeYunet, FACE_SIZE, nms, PLATE_SIZE, TILE_MAX_FACE, tiles, type Box } from './geometry'

ort.env.wasm.numThreads = 1 // pas d'isolation cross-origin : un seul fil, comme sur tous les téléphones

export const MODEL_URLS = {
  face: '/go/models/visages-yunet-2023mar.onnx',
  plate: '/go/models/plaques-yolov9t-384.onnx',
}

let sessions: Promise<{ face: ort.InferenceSession; plate: ort.InferenceSession }> | null = null
function load() {
  sessions ??= Promise.all([
    ort.InferenceSession.create(MODEL_URLS.face, { executionProviders: ['wasm'] }),
    ort.InferenceSession.create(MODEL_URLS.plate, { executionProviders: ['wasm'] }),
  ]).then(([face, plate]) => ({ face, plate }))
  sessions.catch(() => { sessions = null }) // un échec de chargement n'est pas définitif
  return sessions
}

/** Dessine l'image (ou la zone sx, sy, w, h) dans un carré size×size (coin haut-gauche, reste rempli). */
function square(src: CanvasImageSource, w: number, h: number, size: number, fill: string, sx = 0, sy = 0) {
  const ratio = Math.min(size / w, size / h)
  const c = document.createElement('canvas')
  c.width = size; c.height = size
  const g = c.getContext('2d', { willReadFrequently: true })!
  g.fillStyle = fill
  g.fillRect(0, 0, size, size)
  g.drawImage(src, sx, sy, w, h, 0, 0, Math.round(w * ratio), Math.round(h * ratio))
  return { rgba: g.getImageData(0, 0, size, size).data, ratio }
}

function toTensor(rgba: Uint8ClampedArray, size: number, bgr: boolean, scale: number): ort.Tensor {
  const plane = size * size
  const f = new Float32Array(3 * plane)
  for (let i = 0; i < plane; i++) {
    const r = rgba[i * 4], g = rgba[i * 4 + 1], b = rgba[i * 4 + 2]
    f[i] = (bgr ? b : r) * scale; f[plane + i] = g * scale; f[2 * plane + i] = (bgr ? r : b) * scale
  }
  return new ort.Tensor('float32', f, [1, 3, size, size])
}

export interface Detection { boxes: Box[]; ms: number }

export async function detect(src: CanvasImageSource, width: number, height: number): Promise<Detection> {
  const t0 = performance.now()
  const s = await load()
  const faces = async (sx: number, sy: number, w: number, h: number) => {
    const f = square(src, w, h, FACE_SIZE, '#000', sx, sy)
    const out = await s.face.run({ input: toTensor(f.rgba, FACE_SIZE, true, 1) })
    return decodeYunet(out as unknown as Record<string, { data: Float32Array }>, f.ratio).map((b) => ({ ...b, x: b.x + sx, y: b.y + sy }))
  }
  let found = await faces(0, 0, width, height)
  for (const [x0, y0, x1, y1] of tiles(width, height)) { // petits visages, vus de plus près
    found = found.concat((await faces(x0, y0, x1 - x0, y1 - y0)).filter((b) => b.h <= TILE_MAX_FACE * (y1 - y0)))
  }
  const p = square(src, width, height, PLATE_SIZE, 'rgb(114,114,114)')
  const plateOut = await s.plate.run({ images: toTensor(p.rgba, PLATE_SIZE, false, 1 / 255) })
  const boxes = [
    ...nms(found, 0.3),
    ...decodePlates(plateOut.output0 as unknown as { data: Float32Array; dims: number[] }, p.ratio),
  ]
  return { boxes, ms: Math.round(performance.now() - t0) }
}

/** Préchargement discret (écran d'accueil) pour que la première photo ne patiente pas. */
export function warmUp(): void { void load().catch(() => undefined) }
