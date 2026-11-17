// @vitest-environment happy-dom
// SPDX-License-Identifier: AGPL-3.0-or-later
/** Lot C : client API de Salubri Map — session, 401 en lecture et en écriture. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { can, denyReason, getSession, setLoginOpener, setSession } from '../api/session'

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const session = (role: 'moderateur' | 'admin' = 'admin') => ({
  token: 'jeton.signe', expires_at: new Date(Date.now() + 3600e3).toISOString(),
  user: { login: 'awa', display_name: 'Awa', role },
})

beforeEach(() => { setSession(null); setLoginOpener(null); vi.restoreAllMocks(); sessionStorage.clear(); localStorage.clear() })

describe('session', () => {
  it('connexion : jeton en sessionStorage, jamais en localStorage ni en URL', async () => {
    const f = vi.fn(async (_u: string, _i?: RequestInit) => json(200, { ...session(), token_type: 'bearer' }))
    vi.stubGlobal('fetch', f)
    await api.login('awa', 'motdepasse-123')
    expect(getSession()?.user.login).toBe('awa')
    expect(sessionStorage.getItem('salubri_session')).toContain('jeton.signe')
    expect(JSON.stringify(localStorage)).not.toContain('jeton')
    expect(String(f.mock.calls[0][0])).not.toContain('jeton')
  })

  it('envoie le jeton en Bearer, en lecture aussi', async () => {
    setSession(session())
    const f = vi.fn(async (_u: string, init: RequestInit) => json(200, (init.headers as Record<string, string>).Authorization))
    vi.stubGlobal('fetch', f)
    expect(await api.health()).toBe('Bearer jeton.signe')
  })

  it('rôles : admin couvre modérateur, raisons en français', () => {
    expect(denyReason('moderateur', null)).toMatch(/Connectez-vous/)
    expect(can('moderateur', session('admin'))).toBe(true)
    expect(denyReason('admin', session('moderateur'))).toBe('Réservé aux administrateurs (vous êtes modérateur)')
  })

  it('session expirée à la lecture : effacée, pas de panneau de connexion', async () => {
    setSession(session())
    const opener = vi.fn(async () => true)
    setLoginOpener(opener)
    vi.stubGlobal('fetch', vi.fn(async () => json(401, { detail: 'Session expirée' })))
    await expect(api.health()).rejects.toThrow('Session expirée')
    expect(getSession()).toBeNull()
    expect(opener).not.toHaveBeenCalled()
  })

  it('écriture refusée (401) : ouvre le panneau puis réessaie une fois', async () => {
    let n = 0
    vi.stubGlobal('fetch', vi.fn(async () => (++n === 1 ? json(401, { detail: 'Connectez-vous' }) : json(200, { reverted: 3 }))))
    const opener = vi.fn(async () => { setSession(session()); return true })
    setLoginOpener(opener)
    expect(await api.rollback('b1')).toEqual({ reverted: 3 })
    expect(opener).toHaveBeenCalledTimes(1)
    expect(n).toBe(2)
  })

  it('écriture refusée et panneau fermé : l erreur remonte, pas de boucle', async () => {
    const f = vi.fn(async () => json(401, { detail: 'Connectez-vous avec un compte de la mairie' }))
    vi.stubGlobal('fetch', f)
    setLoginOpener(async () => false)
    await expect(api.rollback('b1')).rejects.toThrow(/compte de la mairie/)
    expect(f).toHaveBeenCalledTimes(1)
  })

  it('ancien code 0.2 en localStorage : effacé au chargement', async () => {
    localStorage.setItem('salubri_mairie_code', 'ouaga2026')
    vi.resetModules()
    await import('../api/session')
    expect(localStorage.getItem('salubri_mairie_code')).toBeNull()
  })
})
