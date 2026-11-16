// SPDX-License-Identifier: AGPL-3.0-or-later
/** Outbox IndexedDB : chaque signalement y est enregistré AVANT l'envoi, avec ou sans réseau. */

export type WasteType = 'household' | 'plastic' | 'rubble' | 'organic' | 'medical' | 'mixed' | 'other'
export type VolumeClass = 'bag' | 'wheelbarrow' | 'cart' | 'truck' | 'more'
export interface RuleHit { rule: string; delta: number; detail: string; reject?: boolean }
export interface Verdict { id: string; status: string; score: number; rule_hits: RuleHit[]; already_received?: boolean }

export interface OutboxItem {
  clientId: string
  createdAt: string // heure de la prise (reported_at)
  lat: number
  lon: number
  accuracy: number | null
  wasteType: WasteType
  volumeClass: VolumeClass
  comment: string
  photo: Blob | null
  state: 'pending' | 'sent' | 'error'
  attempts: number
  lastError?: string
  verdict?: Verdict
}

const DB = 'salubri-go'
const STORE = 'outbox'

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'clientId' })
      if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta')
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open()
  return new Promise((resolve, reject) => {
    const r = fn(db.transaction(store, mode).objectStore(store))
    r.onsuccess = () => resolve(r.result)
    r.onerror = () => reject(r.error)
  })
}

export const outbox = {
  put: (item: OutboxItem) => tx(STORE, 'readwrite', (s) => s.put(item)),
  all: async () => (await tx<OutboxItem[]>(STORE, 'readonly', (s) => s.getAll())).sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
  remove: (id: string) => tx(STORE, 'readwrite', (s) => s.delete(id)),
}

/** UUID v4 sans crypto.randomUUID (indisponible hors HTTPS sur téléphone). */
export function uuid(): string {
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

/** Identifiant de l'appareil, créé une fois et gardé dans IndexedDB. */
export async function deviceId(): Promise<string> {
  const v = await tx<string | undefined>('meta', 'readonly', (s) => s.get('device_id') as IDBRequest<string | undefined>)
  if (v) return v
  const id = uuid()
  await tx('meta', 'readwrite', (s) => s.put(id, 'device_id'))
  return id
}
