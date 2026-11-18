// SPDX-License-Identifier: AGPL-3.0-or-later
import { useCallback, useEffect, useRef, useState } from 'react'
import { playCue, stopAudio } from './player'
import type { Cue, Lang } from './script'

interface Opts { repeat?: number; pauseMs?: number; enabled?: boolean }

/** Dit les `cues` l'un après l'autre ; `glow` désigne l'élément qui brille pendant qu'il est dit. Rejoue `repeat` fois
 *  (le public hésite) avec une pause entre deux passages. Si le navigateur refuse le son, le premier toucher le relance. */
export function useCues(lang: Lang | ((i: number) => Lang), cues: Cue[], { repeat = 1, pauseMs = 5000, enabled = true }: Opts = {}) {
  const [glow, setGlow] = useState<string | null>(null)
  const [blocked, setBlocked] = useState(false)
  const run = useRef(0)
  const cuesRef = useRef(cues)
  cuesRef.current = cues
  const langRef = useRef(lang)
  langRef.current = lang

  const start = useCallback(() => {
    const token = ++run.current
    const alive = () => token === run.current
    stopAudio()
    void (async () => {
      setBlocked(false)
      for (let pass = 0; pass < repeat; pass++) {
        for (const [i, c] of cuesRef.current.entries()) {
          if (!alive()) return
          setGlow(c.glow ?? null)
          const l = typeof langRef.current === 'function' ? langRef.current(i) : langRef.current
          const r = await playCue(l, c.id, c.fallbackMs)
          if (!alive()) return
          if (r === 'blocked') { setBlocked(true); setGlow(null); return }
        }
        setGlow(null)
        if (pass < repeat - 1) await new Promise<void>((res) => window.setTimeout(res, pauseMs))
      }
      if (alive()) setGlow(null)
    })()
  }, [repeat, pauseMs])

  const stop = useCallback(() => { run.current++; stopAudio(); setGlow(null) }, [])

  const key = cues.map((c) => c.id).join('|')
  useEffect(() => {
    if (!enabled || cues.length === 0) return
    start()
    return () => { run.current++; stopAudio() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled, typeof lang === 'string' ? lang : 'multi'])

  // son refusé par le navigateur : le premier toucher n'importe où relance la séquence
  useEffect(() => {
    if (!blocked) return
    const go = () => start()
    window.addEventListener('pointerdown', go, { once: true, capture: true })
    return () => window.removeEventListener('pointerdown', go, { capture: true } as EventListenerOptions)
  }, [blocked, start])

  return { glow, blocked, replay: start, stop }
}
