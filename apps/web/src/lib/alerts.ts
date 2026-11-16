// SPDX-License-Identifier: AGPL-3.0-or-later
import { api } from '../api/client'
import type { Scenario } from '../api/types'
import { AUDIT_ACTION } from './labels'

export interface Alert { id: string; level: 'red' | 'orange' | 'blue' | 'green'; text: string; at: string | null }

export async function loadAlerts(sc: Scenario | null): Promise<Alert[]> {
  const out: Alert[] = []
  if (sc) {
    for (const v of sc.vehicles.filter((v) => v.out_of_service)) {
      out.push({ id: `v-${v.id}`, level: 'red', text: `Camion ${v.label} en panne`, at: sc.updated_at })
    }
    if (sc.latest_ready_plan_id) {
      const pts = await api.points(sc.latest_ready_plan_id)
      const unserved = pts.features.filter((f) => f.properties.unserved)
      if (unserved.length) out.push({ id: 'unserved', level: 'red', text: `${unserved.length} point(s) de regroupement non desservi(s)`, at: null })
      const full = pts.features.filter((f) => (f.properties.fill_ratio_per_pickup ?? 0) > 1)
      for (const f of full.slice(0, 3)) {
        out.push({ id: `full-${f.properties.key}`, level: 'orange', text: `Point ${f.properties.key} saturé (${Math.round((f.properties.fill_ratio_per_pickup ?? 0) * 100)} %)`, at: null })
      }
    }
  }
  const rej = await api.reports({ status: ['rejected', 'to_review'], limit: 4 })
  for (const f of rej.features) {
    const r = f.properties
    out.push({ id: `r-${r.id}`, level: r.status === 'rejected' ? 'orange' : 'blue',
               text: `Signalement ${r.status === 'rejected' ? 'rejeté' : 'à revoir'} : ${r.rule_hits[0]?.detail ?? 'règles déclenchées'}`, at: r.received_at })
  }
  const audit = await api.audit(4)
  for (const a of audit) {
    out.push({ id: `a-${a.id}`, level: 'green', text: `${AUDIT_ACTION[a.action] ?? a.action} (${a.entity})`, at: a.at })
  }
  return out
}
