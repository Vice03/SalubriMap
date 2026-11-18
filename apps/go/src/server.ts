// SPDX-License-Identifier: AGPL-3.0-or-later
/** Application Android (Capacitor) : l'adresse du serveur Salubri est saisie au premier lancement. Le PWA garde son origine. */
const KEY = 'salubri-server'

export function isNative(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean((window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor?.isNativePlatform?.())
}

/** « 192.168.1.20 » → « http://192.168.1.20 » (sans « / » final). */
export function normalizeServer(raw: string): string {
  const s = raw.trim().replace(/\/+$/, '')
  if (!s) return ''
  return /^https?:\/\//i.test(s) ? s : `http://${s}`
}

export function getServer(): string {
  try { return localStorage.getItem(KEY) ?? '' } catch { return '' }
}
export function setServer(addr: string): void {
  try { if (addr) localStorage.setItem(KEY, addr); else localStorage.removeItem(KEY) } catch { /* stockage indisponible */ }
}

/** Adresse d'un appel API : relative dans le PWA, préfixée par le serveur enregistré dans l'application Android. */
export function apiUrl(path: string): string {
  return isNative() ? getServer() + path : path
}

/** Adresse privée seulement (10.x, 172.16-31.x, 192.168.x, localhost) : l'application Android autorise le texte clair vers elle seule. */
export function estReseauLocal(base: string): boolean {
  let host: string
  try { host = new URL(base).hostname } catch { return false }
  if (host === 'localhost' || host === '127.0.0.1') return true
  const m = /^(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}$/.exec(host)
  if (!m) return false
  const a = Number(m[1]), b = Number(m[2])
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168)
}
