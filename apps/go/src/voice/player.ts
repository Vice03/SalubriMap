// SPDX-License-Identifier: AGPL-3.0-or-later
import { audioUrl, type Lang } from './script'

/** ended : dit en entier · missing : fichier absent (on attend quand même, pour garder le rythme) ·
 *  blocked : le navigateur refuse de lire sans toucher l'écran · stopped : coupé par une autre voix ou un clic. */
export type PlayResult = 'ended' | 'missing' | 'blocked' | 'stopped'

let el: HTMLAudioElement | null = null
let cancel: (() => void) | null = null

export function stopAudio(): void { cancel?.() }

/** Joue un fichier du guide vocal ; une seule voix à la fois. Un fichier absent n'est jamais une erreur. */
export function playCue(lang: Lang, id: string, fallbackMs = 1200): Promise<PlayResult> {
  stopAudio()
  return new Promise<PlayResult>((resolve) => {
    if (typeof Audio === 'undefined') { window.setTimeout(() => resolve('missing'), fallbackMs); return }
    const a = (el ??= new Audio()) // le même élément : une fois débloqué par un toucher, il le reste
    let done = false
    let timer: number | undefined
    const finish = (r: PlayResult) => {
      if (done) return
      done = true
      window.clearTimeout(timer)
      a.onended = null; a.onerror = null
      if (cancel === stop) cancel = null
      resolve(r)
    }
    const missing = () => { if (!done && timer === undefined) timer = window.setTimeout(() => finish('missing'), fallbackMs) }
    const stop = () => { a.pause(); finish('stopped') }
    cancel = stop
    a.onended = () => finish('ended')
    a.onerror = missing
    a.src = audioUrl(lang, id)
    a.play().catch((e: unknown) => {
      if ((e as { name?: string })?.name === 'NotAllowedError') finish('blocked')
      else missing() // NotSupportedError : fichier absent ou illisible
    })
  })
}
