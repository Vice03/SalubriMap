// SPDX-License-Identifier: AGPL-3.0-or-later
/** Lot C : file d'attente hors ligne de Salubri Go (réessai, 429, idempotence). */
import 'fake-indexeddb/auto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { deviceId, outbox, uuid, type OutboxItem } from '../db'
import { syncOutbox } from '../sync'

const item = (n: number, extra: Partial<OutboxItem> = {}): OutboxItem => ({
  clientId: `c-${n}`, createdAt: `2026-11-17T08:0${n}:00Z`, lat: 12.37, lon: -1.52, accuracy: 8,
  wasteType: 'household', volumeClass: 'cart', comment: '', photo: null, state: 'pending', attempts: 0, ...extra,
})
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

beforeEach(async () => {
  for (const i of await outbox.all()) await outbox.remove(i.clientId)
  vi.restoreAllMocks()
})

describe('outbox', () => {
  it('garde un identifiant d appareil stable et des UUID v4', async () => {
    const a = await deviceId()
    expect(await deviceId()).toBe(a)
    expect(uuid()).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
  })

  it('envoie dans l ordre de prise et marque « envoyé » avec le verdict', async () => {
    await outbox.put(item(1)); await outbox.put(item(2))
    const sent: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init: RequestInit) => {
      sent.push((init.body as FormData).get('client_id') as string)
      return json(201, { id: 'r', status: 'probable', score: 80, rule_hits: [] })
    }))
    expect(await syncOutbox()).toBe(2)
    expect(sent).toEqual(['c-1', 'c-2'])
    expect((await outbox.all()).every((i) => i.state === 'sent' && i.verdict?.score === 80)).toBe(true)
  })

  it('hors ligne : rien n est perdu, nouvel essai plus tard', async () => {
    await outbox.put(item(1))
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    expect(await syncOutbox()).toBe(0)
    const [i] = await outbox.all()
    expect(i.state).toBe('pending')
    expect(i.attempts).toBe(1)
    expect(i.lastError).toMatch(/Pas de réseau/)
  })

  it('429 : reste en attente avec le motif du serveur et arrête la tournée', async () => {
    await outbox.put(item(1)); await outbox.put(item(2))
    const f = vi.fn(async () => json(429, { detail: 'Trop de signalements envoyés par ce téléphone (30 en 1 h).' }))
    vi.stubGlobal('fetch', f)
    expect(await syncOutbox()).toBe(0)
    expect(f).toHaveBeenCalledTimes(1) // inutile d'insister sur les suivants
    const all = await outbox.all()
    expect(all.every((i) => i.state === 'pending')).toBe(true)
    expect(all.find((i) => i.clientId === 'c-1')?.lastError).toMatch(/Trop de signalements/)
  })

  it('5xx : réessai, et le signalement n est pas compté comme envoyé', async () => {
    await outbox.put(item(1))
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oups', { status: 502 })))
    expect(await syncOutbox()).toBe(0)
    expect((await outbox.all())[0].state).toBe('pending')
  })

  it('refus du contenu (422) : « erreur » avec le message, sans compter un envoi', async () => {
    await outbox.put(item(1))
    vi.stubGlobal('fetch', vi.fn(async () => json(422, { detail: 'Fichier image illisible' })))
    expect(await syncOutbox()).toBe(0)
    const [i] = await outbox.all()
    expect(i.state).toBe('error')
    expect(i.lastError).toBe('Fichier image illisible')
  })

  it('idempotence : le même client_id est renvoyé tel quel, le serveur répond « déjà reçu »', async () => {
    await outbox.put(item(1))
    const ids: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init: RequestInit) => {
      ids.push((init.body as FormData).get('client_id') as string)
      return ids.length === 1 ? new Response('', { status: 503 }) : json(200, { id: 'r', status: 'probable', score: 70, rule_hits: [], already_received: true })
    }))
    await syncOutbox()
    expect(await syncOutbox()).toBe(1)
    expect(ids).toEqual(['c-1', 'c-1'])
    expect((await outbox.all())[0].verdict?.already_received).toBe(true)
  })

  it('un seul envoi à la fois même si on relance pendant la tournée', async () => {
    await outbox.put(item(1))
    let calls = 0
    vi.stubGlobal('fetch', vi.fn(async () => { calls++; await new Promise((r) => setTimeout(r, 20)); return json(201, { id: 'r', status: 'probable', score: 90, rule_hits: [] }) }))
    const [a, b] = await Promise.all([syncOutbox(), syncOutbox()])
    expect(a).toBe(1); expect(b).toBe(1); expect(calls).toBe(1)
  })
})
