// SPDX-License-Identifier: AGPL-3.0-or-later
import { deviceId, outbox, type OutboxItem, type Steps, type Verdict } from './db'

let running: Promise<number> | null = null

async function thumbnail(photo: Blob): Promise<Blob | null> {
  try {
    if (typeof createImageBitmap === 'undefined' || typeof document === 'undefined') return null
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

/** true si le serveur a accepté (créé ou déjà reçu), false s'il a refusé le contenu ; lève une erreur pour réessayer. */
async function send(item: OutboxItem, device: string): Promise<boolean> {
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
  if (item.exif?.lat != null && item.exif.lon != null) { f.append('exif_lat', String(item.exif.lat)); f.append('exif_lon', String(item.exif.lon)) }
  if (item.exif?.takenAt) f.append('exif_taken_at', item.exif.takenAt)
  if (item.masking) f.append('masking_client', JSON.stringify(item.masking))
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
    return true
  } else if (res.status === 429) {
    // trop d'envois : le signalement reste « En attente » et repart au prochain essai automatique
    let msg = 'Trop d\'envois pour le moment : nouvel essai automatique'
    try { const b = await res.json(); if (typeof b.detail === 'string') msg = b.detail } catch { /* corps non JSON */ }
    await outbox.put({ ...item, attempts: item.attempts + 1, lastError: msg })
    throw new Error('throttled') // inutile d'envoyer les suivants tout de suite
  } else if (res.status >= 500) {
    await outbox.put({ ...item, attempts: item.attempts + 1, lastError: `Serveur indisponible (${res.status}) : nouvel essai automatique` })
    throw new Error('server')
  } else {
    let msg = `Refusé (${res.status})`
    try { const b = await res.json(); msg = b.detail ? (typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail)) : msg } catch { /* corps non JSON */ }
    await outbox.put({ ...item, state: 'error', lastError: msg })
    return false
  }
  return false
}

/** Envoie tout ce qui attend ; renvoie le nombre de signalements envoyés. */
export function syncOutbox(): Promise<number> {
  running ??= (async () => {
    let sent = 0
    try {
      const device = await deviceId()
      for (const item of (await outbox.all()).filter((i) => i.state === 'pending').reverse()) {
        try { if (await send(item, device)) sent++ } catch { break } // hors ligne, 429, 5xx : on arrête et on réessaiera
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

/** Suivi (lot D) : relit statut et étapes des signalements envoyés, par leur client_id. */
export async function refreshFollowUp(): Promise<void> {
  const sent = (await outbox.all()).filter((i) => i.state === 'sent' && i.verdict)
  if (!sent.length || !navigator.onLine) return
  const q = sent.map((i) => `client_id=${encodeURIComponent(i.clientId)}`).join('&')
  try {
    const res = await fetch(`/api/reports/suivi?${q}`)
    if (!res.ok) return
    const rows = (await res.json()) as { client_id: string; status: string; steps: Steps; rule_hits: Verdict['rule_hits'] }[]
    for (const r of rows) {
      const it = sent.find((i) => i.clientId === r.client_id)
      if (it?.verdict) await outbox.put({ ...it, verdict: { ...it.verdict, status: r.status, steps: r.steps, rule_hits: r.rule_hits } })
    }
    notify()
  } catch { /* hors ligne : on garde le dernier état connu */ }
}
