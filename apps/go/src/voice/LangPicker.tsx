// SPDX-License-Identifier: AGPL-3.0-or-later
import { Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { syncOutbox } from '../sync'
import { LANG_CUES, type Lang, type LangChoice } from './script'
import { useCues } from './useCues'

const CHOIX: { k: Lang; label: string; flag: string }[] = [
  { k: 'fr', label: 'Français', flag: '🇫🇷' },
  { k: 'mos', label: 'Mooré', flag: '🇧🇫' },
]

/** Écran de langue, au lancement après la synchronisation : une voix par langue, le bouton de la langue qui parle brille. */
export function LangPicker({ onPick }: { onPick: (l: LangChoice) => void }) {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let alive = true
    // « après synchro » : on laisse partir les envois en attente (4 s au plus, hors ligne ou serveur lent)
    void Promise.race([syncOutbox().catch(() => 0), new Promise((r) => window.setTimeout(r, 4000))]).then(() => { if (alive) setReady(true) })
    return () => { alive = false }
  }, [])
  const { glow, blocked, replay } = useCues((i) => LANG_CUES[i]!.lang, LANG_CUES.map((c) => c.cue), { repeat: 4, pauseMs: 3000, enabled: ready })
  return (
    <div className="vg-lang">
      <div className="vg-logo"><img src={`${import.meta.env.BASE_URL}icon.svg`} alt="" /><b>Salubri <span>Go</span></b></div>
      {!ready && <p className="vg-wait" role="status"><Volume2 size={28} className="spin" /></p>}
      {ready && (
        <>
          <div className="vg-big">
            {CHOIX.map((c) => (
              <button key={c.k} className={`vg-choice glow ${glow === c.k ? 'glow-on' : ''}`} onClick={() => onPick(c.k)} aria-label={c.label}>
                <span className="vg-flag" aria-hidden>{c.flag}</span><span>{c.label}</span><Volume2 size={30} aria-hidden />
              </button>
            ))}
          </div>
          {blocked && <p className="vg-unlock" role="status"><Volume2 size={22} />Touchez l'écran pour entendre la voix</p>}
          <button className="icon vg-replay" aria-label="Réécouter" onClick={replay}><Volume2 size={22} /></button>
          <button className="link" onClick={() => onPick('off')}>Continuer sans voix</button>
        </>
      )}
    </div>
  )
}
