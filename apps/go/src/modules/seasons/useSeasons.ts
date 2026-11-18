// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from 'react'
import { apiUrl } from '../../server'

/** Module « Saisons » allumé côté serveur ? (/api/health → modules.seasons). Faux hors ligne ou s'il est éteint. */
export function useSeasonsEnabled(): boolean {
  const [on, setOn] = useState(false)
  useEffect(() => {
    let alive = true
    fetch(apiUrl('/api/health')).then((r) => r.json()).then((h) => { if (alive) setOn(Boolean(h?.modules?.seasons)) }).catch(() => {})
    return () => { alive = false }
  }, [])
  return on
}
