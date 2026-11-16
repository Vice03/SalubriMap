// SPDX-License-Identifier: AGPL-3.0-or-later
import { api } from './client'
import type { PlanSummary, StageRecord } from './types'

export interface FollowHandlers {
  onStage?: (s: StageRecord & { running?: boolean }) => void
  onReady?: (planId: string, summary: PlanSummary) => void
  onFailed?: (error: string) => void
}

/** Follow a recompute: SSE first, polling fallback; follows `superseded` to the newer version. */
export function followPlan(planId: string, h: FollowHandlers): () => void {
  let closed = false
  let es: EventSource | null = null
  let timer: number | undefined

  const finishFromPlan = async (id: string) => {
    const p = await api.plan(id)
    if (p.status === 'superseded') {
      const sc = await api.scenario(p.scenario_id)
      if (sc.latest_plan_id && sc.latest_plan_id !== id) return start(sc.latest_plan_id)
    }
    if (p.status === 'ready') h.onReady?.(id, p.summary)
    else if (p.status === 'failed') h.onFailed?.(p.error ?? 'Échec du recalcul')
  }

  const poll = (id: string) => {
    timer = window.setInterval(async () => {
      if (closed) return
      try {
        const p = await api.plan(id)
        if (['ready', 'failed', 'superseded'].includes(p.status)) {
          window.clearInterval(timer)
          p.stages.forEach((s) => h.onStage?.(s))
          await finishFromPlan(id)
        }
      } catch { /* keep polling */ }
    }, 300)
  }

  const start = (id: string) => {
    if (closed) return
    es?.close()
    es = new EventSource(`/api/plans/${id}/events`)
    es.addEventListener('stage_started', (e) => {
      const d = JSON.parse((e as MessageEvent).data)
      h.onStage?.({ stage: d.stage, name: d.name, duration_ms: 0, cache_hit: false, running: true })
    })
    es.addEventListener('stage_done', (e) => h.onStage?.(JSON.parse((e as MessageEvent).data)))
    const end = () => { es?.close(); void finishFromPlan(id) }
    es.addEventListener('ready', end)
    es.addEventListener('failed', end)
    es.addEventListener('superseded', end)
    es.onerror = () => { es?.close(); if (!closed) poll(id) }
  }

  start(planId)
  return () => { closed = true; es?.close(); window.clearInterval(timer) }
}
