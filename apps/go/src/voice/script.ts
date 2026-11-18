// SPDX-License-Identifier: AGPL-3.0-or-later
/** Guide vocal de Salubri Go : langues, identifiants des fichiers audio (voir docs/AUDIO_GO.md) et séquences de chaque étape. */
import { VOLUME, WASTE } from '../labels'

export type Lang = 'fr' | 'mos'
export type LangChoice = Lang | 'off' // « off » : formulaire classique, sans voix

const KEY = 'salubri-go-lang'
export function getLang(): LangChoice | null {
  try { const v = localStorage.getItem(KEY); return v === 'fr' || v === 'mos' || v === 'off' ? v : null } catch { return null }
}
export function setLang(v: LangChoice | null): void {
  try { if (v) localStorage.setItem(KEY, v); else localStorage.removeItem(KEY) } catch { /* stockage indisponible */ }
}

/** Un fichier audio à dire, et l'élément de l'écran qui brille pendant qu'il est dit. */
export interface Cue { id: string; glow?: string; fallbackMs?: number }

/** Fichiers propres à l'écran de langue : chaque langue y est présentée dans sa propre voix. */
export const LANG_CUES: { lang: Lang; cue: Cue }[] = [
  { lang: 'fr', cue: { id: 'lang_fr', glow: 'fr', fallbackMs: 2200 } },
  { lang: 'mos', cue: { id: 'lang_mos', glow: 'mos', fallbackMs: 2200 } },
]

export const photoAsk: Cue[] = [{ id: 'photo_ask', glow: 'camera', fallbackMs: 2500 }]
export const photoContinue: Cue[] = [{ id: 'photo_continue', glow: 'continue', fallbackMs: 2500 }]
export const qtyCues: Cue[] = [
  { id: 'qty_ask', fallbackMs: 2000 },
  ...VOLUME.map((v) => ({ id: `qty_${v.k}`, glow: v.k, fallbackMs: 1300 })),
]
export const typeCues: Cue[] = [
  { id: 'type_ask', fallbackMs: 2000 },
  ...WASTE.map((w) => ({ id: `type_${w.k}`, glow: w.k, fallbackMs: 1300 })),
]
export const locAsk: Cue[] = [{ id: 'loc_ask', glow: 'loc', fallbackMs: 3000 }]
export const locWait: Cue[] = [{ id: 'loc_wait', fallbackMs: 2000 }]
export const locDenied: Cue[] = [{ id: 'loc_denied', glow: 'loc', fallbackMs: 3500 }]
export const thanksCues = (online: boolean): Cue[] => [
  { id: online ? 'thanks' : 'thanks_offline', fallbackMs: 2500 },
  { id: 'again', glow: 'again', fallbackMs: 2500 },
]

/** Tous les fichiers d'une langue (hors écran de langue) : sert à vérifier qu'aucun n'est oublié. */
export const AUDIO_IDS: string[] = [
  ...photoAsk, ...photoContinue, ...qtyCues, ...typeCues, ...locAsk, ...locWait, ...locDenied, ...thanksCues(true), ...thanksCues(false),
].map((c) => c.id).filter((id, i, a) => a.indexOf(id) === i)

export function audioUrl(lang: Lang, id: string): string {
  return `${import.meta.env.BASE_URL}audio/${lang}/${id}.mp3`
}
