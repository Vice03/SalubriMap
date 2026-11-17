// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from 'react'

export interface Modules { seasons: boolean; assistant: boolean }

/** Modules optionnels allumés côté serveur (/api/health → modules). Tout est caché tant qu'ils sont éteints. */
export function useModules(): Modules {
  const [m, setM] = useState<Modules>({ seasons: false, assistant: false })
  useEffect(() => {
    let alive = true
    fetch('/api/health').then((r) => r.json()).then((h) => {
      if (alive && h?.modules) setM({ seasons: !!h.modules.seasons, assistant: !!h.modules.assistant })
    }).catch(() => {})
    return () => { alive = false }
  }, [])
  return m
}
