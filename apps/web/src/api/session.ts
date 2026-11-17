// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Session de la mairie (lot A7) : jeton gardé en mémoire et dans sessionStorage (onglet seulement,
 * effacé à la fermeture), jamais dans une URL ni dans localStorage.
 */
import { useSyncExternalStore } from 'react'

export type Role = 'moderateur' | 'admin'
export interface SessionUser { login: string; display_name: string; role: Role }
export interface Session { token: string; expires_at: string; user: SessionUser }

const KEY = 'salubri_session'
const ROLE_LABEL: Record<Role, string> = { moderateur: 'modérateur', admin: 'administrateur' }
const GRANTS: Record<Role, Role[]> = { moderateur: ['moderateur', 'admin'], admin: ['admin'] }

function load(): Session | null {
  try {
    localStorage.removeItem('salubri_mairie_code') // ancien code (0.2) : ne plus le garder sur le disque
    const s = JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as Session | null
    return s && new Date(s.expires_at).getTime() > Date.now() ? s : null
  } catch { return null }
}

let current: Session | null = load()
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())

export function getSession(): Session | null {
  if (current && new Date(current.expires_at).getTime() <= Date.now()) setSession(null)
  return current
}

export function setSession(s: Session | null): void {
  current = s
  try { if (s) sessionStorage.setItem(KEY, JSON.stringify(s)); else sessionStorage.removeItem(KEY) } catch { /* stockage indisponible : mémoire seule */ }
  emit()
}

export function authHeaders(): Record<string, string> {
  const s = getSession()
  return s ? { Authorization: `Bearer ${s.token}` } : {}
}

export function roleLabel(r: Role): string { return ROLE_LABEL[r] }

/** Le compte connecté a-t-il le rôle demandé ? (admin couvre modérateur) */
export function can(need: Role, s: Session | null = getSession()): boolean {
  return !!s && GRANTS[need].includes(s.user.role)
}

/** Raison affichée sur un bouton désactivé, ou null si l'action est permise. */
export function denyReason(need: Role, s: Session | null = getSession()): string | null {
  if (can(need, s)) return null
  if (!s) return need === 'admin' ? 'Connectez-vous avec un compte administrateur' : 'Connectez-vous avec un compte de la mairie'
  return `Réservé aux ${need === 'admin' ? 'administrateurs' : 'modérateurs'} (vous êtes ${ROLE_LABEL[s.user.role]})`
}

export function useSession(): Session | null {
  return useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l) }, getSession, getSession)
}

// Le panneau de connexion s'enregistre ici ; le client API l'ouvre sur un 401 d'écriture.
let opener: ((why?: string) => Promise<boolean>) | null = null
export function setLoginOpener(fn: typeof opener): void { opener = fn }
export function askLogin(why?: string): Promise<boolean> { return opener ? opener(why) : Promise.resolve(false) }
