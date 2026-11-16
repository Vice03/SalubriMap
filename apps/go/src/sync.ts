// SPDX-License-Identifier: AGPL-3.0-or-later
import { deviceId, outbox, type OutboxItem, type Verdict } from './db'

let running: Promise<number> | null = null

async function thumbnail(photo: Blob): Promise<Blob | null> {
  try {
    const bmp = await createImageBitmap(photo)
    const k = 160 / Math.max(bmp.width, bmp.height)
    const c = document.createElement('canvas')
    c.width = Math.round(bmp.width * k)
    c.height = Math.round(bmp.height * k)
    c.getContext('2d')!.drawImage(bmp, 0, 0, c.width, c.height)
    return await new Promise((res) => c.toBlob((b) => res(b), 'image/jpeg', 0.7))
  } catch { return null }
}
const listeners = new Set<() => void>()
export const onOutboxChange = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }
export const notify = () => listeners.forEach((fn) => fn())

async function send(item: OutboxItem, device: string): Promise<void> {
  const f = new FormData()
  f.append('lat', item.lat.toFixed(7))
  f.append('lon', item.lon.toFixed(7))
  if (item.accuracy != null) f.append('accuracy', String(Math.round(item.accuracy)))
  f.append('waste_type', item.wasteType)
  f.append('volume_class', item.volumeClass)
  if (item.comment) f.append('comment', item.comment.slice(0, 1000))
  f.append('reported_at', item.createdAt)
  f.append('device_id', device)
  f.append('client_id', item.clientId) // envoi idempotent : un renvoi ne crée jamais de doublon
  if (item.photo) f.append('photo', item.photo, 'photo.jpg')
  let res: Response
  try {
    res = await fetch('/api/reports', { method: 'POST', body: f })
  } catch {
    await outbox.put({ ...item, attempts: item.attempts + 1, lastError: 'Pas de réseau : nouvel essai automatique' })
    throw new Error('offline')
  }
  if (res.ok) {
    const verdict = (await res.json()) as Verdict
    // la photo est sur le serveur : on ne garde qu'une vignette pour ne pas remplir le téléphone
    await outbox.put({ ...item, state: 'sent', verdict, lastError: undefined, photo: item.photo ? await thumbnail(item.photo) : null })
  } else if (res.status >= 500) {
    await outbox.put({ ...item, attempts: item.attempts + 1, lastError: `Serveur indisponible (${res.status}) : nouvel essai automatique` })
  } else {
    let msg = `Refusé (${res.status})`
    try { const b = await res.json(); msg = b.detail ? (typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail)) : msg } catch { /* corps non JSON */ }
    await outbox.put({ ...item, state: 'error', lastError: msg })
  }
}

/** Envoie tout ce qui attend ; renvoie le nombre de signalements envoyés. */
export function syncOutbox(): Promise<number> {
  running ??= (async () => {
    let sent = 0
    try {
      const device = await deviceId()
      for (const item of (await outbox.all()).filter((i) => i.state === 'pending').reverse()) {
        try { await send(item, device); sent++ } catch { break } // hors ligne : on arrête et on réessaiera
        notify()
      }
    } finally { running = null; notify() }
    return sent
  })()
  return running
}

export function startAutoSync(): () => void {
  const tick = () => { if (navigator.onLine) void syncOutbox() }
  window.addEventListener('online', tick)
  const t = window.setInterval(tick, 30_000)
  tick()
  return () => { window.removeEventListener('online', tick); window.clearInterval(t) }
}
