// SPDX-License-Identifier: AGPL-3.0-or-later
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { followPlan } from '../api/sse'
import type { PlanSummary, Scenario, StageRecord } from '../api/types'

export interface Toast { id: number; kind: 'ok' | 'error' | 'info'; text: string }
export interface Tracking { planId: string; label: string; stages: Record<string, StageRecord & { running?: boolean }>; done: boolean; failed?: string; startedAt: number; totalMs?: number }

interface AppState {
  scenarios: Scenario[]
  scenario: Scenario | null
  setScenarioId: (id: string) => void
  reloadScenarios: () => Promise<void>
  refreshKey: number
  refresh: () => void
  tracking: Tracking | null
  track: (planId: string, label: string) => void
  toasts: Toast[]
  toast: (kind: Toast['kind'], text: string) => void
}

const Ctx = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [scenarioId, setScenarioId] = useState<string | null>(() => localStorageGet('salubri.scenario'))
  const [refreshKey, setRefreshKey] = useState(0)
  const [tracking, setTracking] = useState<Tracking | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const stopRef = useRef<(() => void) | null>(null)
  const lastPlanRef = useRef<string | null>(null)

  const toast = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, kind, text }])
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
  }, [])

  const reloadScenarios = useCallback(async () => {
    try {
      setScenarios(await api.scenarios())
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }, [toast])

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  const track = useCallback((planId: string, label: string) => {
    stopRef.current?.()
    const t0 = performance.now()
    setTracking({ planId, label, stages: {}, done: false, startedAt: t0 })
    stopRef.current = followPlan(planId, {
      onStage: (s) => setTracking((tr) => (tr ? { ...tr, stages: { ...tr.stages, [s.stage]: s } } : tr)),
      onReady: (_id: string, summary: PlanSummary) => {
        setTracking((tr) => (tr ? { ...tr, done: true, totalMs: performance.now() - t0 } : tr))
        toast('ok', summary.diff?.text ? `Plan recalculé : ${summary.diff.text}` : 'Plan recalculé')
        void reloadScenarios().then(refresh)
        window.setTimeout(() => setTracking((tr) => (tr && tr.planId === planId ? null : tr)), 8000)
      },
      onFailed: (err) => {
        setTracking((tr) => (tr ? { ...tr, done: true, failed: err } : tr))
        toast('error', `Échec du recalcul : ${err}. L'ancien plan reste affiché.`)
      },
    })
  }, [reloadScenarios, refresh, toast])

  useEffect(() => { void reloadScenarios() }, [reloadScenarios])

  // Detect recomputes started elsewhere (imports, moderation): poll the selected scenario.
  const scenario = useMemo(
    () => scenarios.find((s) => s.id === scenarioId) ?? scenarios.find((s) => s.is_baseline) ?? scenarios[0] ?? null,
    [scenarios, scenarioId],
  )
  useEffect(() => {
    if (!scenario) return
    const iv = window.setInterval(async () => {
      try {
        const sc = await api.scenario(scenario.id)
        if (sc.latest_plan_id && sc.latest_plan_id !== lastPlanRef.current) {
          const prev = lastPlanRef.current
          lastPlanRef.current = sc.latest_plan_id
          if (prev && (sc.latest_plan_status === 'pending' || sc.latest_plan_status === 'running') && !tracking) {
            track(sc.latest_plan_id, 'Recalcul automatique')
          } else if (prev && sc.latest_plan_status === 'ready') {
            void reloadScenarios().then(refresh)
          }
        }
      } catch { /* offline: ignore */ }
    }, 4000)
    lastPlanRef.current = scenario.latest_plan_id
    return () => window.clearInterval(iv)
  }, [scenario, track, tracking, reloadScenarios, refresh])

  const value: AppState = {
    scenarios, scenario,
    setScenarioId: (id) => { localStorageSet('salubri.scenario', id); setScenarioId(id) },
    reloadScenarios, refreshKey, refresh, tracking, track, toasts, toast,
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('AppProvider manquant')
  return v
}

function localStorageGet(k: string): string | null {
  try { return window.localStorage.getItem(k) } catch { return null }
}
function localStorageSet(k: string, v: string): void {
  try { window.localStorage.setItem(k, v) } catch { /* ignore */ }
}

/** Fetch helper: re-runs when deps or the global refresh key change. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null; loading: boolean; reload: () => void } {
  const { refreshKey } = useApp()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [n, setN] = useState(0)
  useEffect(() => {
    let alive = true
    setLoading(true)
    fn().then((d) => { if (alive) { setData(d); setError(null) } })
      .catch((e: Error) => { if (alive) setError(e.message) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refreshKey, n])
  return { data, error, loading, reload: () => setN((x) => x + 1) }
}
