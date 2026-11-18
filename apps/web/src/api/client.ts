// SPDX-License-Identifier: AGPL-3.0-or-later
/// <reference types="geojson" />
import type {
  AuditEntry, Commune, CompareMany, CompareResult, DumpProps, FC, Feature, Health, ImportResult, LineGeom, ParamsSchema,
  Plan, PointGeom, PointProps, PolyGeom, QuartierProps, ReportProps, ReportStatus, RouteProps, Scenario, Stats,
  ValidationRules, Vehicle,
} from './types'
import type { LaabalAlerts } from '../lib/laabal'
import type { WaterDumps } from './types'
import { askLogin, authHeaders, getSession, setSession, type Session } from './session'

export class ApiError extends Error {
  constructor(public status: number, public title: string, public detail: string) {
    super(detail || title)
  }
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>

function qs(q?: Query): string {
  if (!q) return ''
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x))
    else p.append(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

/** Photo d'un signalement : chargée avec la session, car celles des signalements non vérifiés sont réservées. */
export async function photoObjectUrl(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { headers: authHeaders() })
    return res.ok ? URL.createObjectURL(await res.blob()) : null
  } catch { return null }
}

/** Les écritures (modération, imports, scénarios, flotte) exigent le code d'accès mairie. */
async function request<T>(method: string, path: string, opts: { query?: Query; json?: unknown; form?: FormData } = {}, retry = true): Promise<T> {
  // la session est aussi envoyée en lecture : la mairie voit alors les signalements non vérifiés (lot A4)
  const init: RequestInit = { method, headers: authHeaders() }
  if (opts.json !== undefined) {
    init.body = JSON.stringify(opts.json)
    ;(init.headers as Record<string, string>)['Content-Type'] = 'application/json'
  } else if (opts.form) init.body = opts.form
  let res: Response
  try {
    res = await fetch(`/api${path}${qs(opts.query)}`, init)
  } catch {
    throw new ApiError(0, 'Réseau', "Impossible de joindre le serveur Salubri")
  }
  if (res.status === 401) {
    if (getSession() && !path.startsWith('/auth/')) setSession(null) // session expirée ou révoquée
    // une écriture refusée ouvre le panneau de connexion puis réessaie ; une lecture ne l'ouvre jamais
    if (retry && method !== 'GET' && !path.startsWith('/auth/') && (await askLogin())) return request<T>(method, path, opts, false)
  }
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : body.title ?? `Erreur ${res.status}`
    throw new ApiError(res.status, body.title ?? 'Erreur', res.status === 503 ? 'Le serveur démarre, réessayez dans une minute' : detail)
  }
  return body as T
}

const get = <T,>(p: string, q?: Query) => request<T>('GET', p, { query: q })

export const api = {
  /** Connexion : le jeton reste dans cet onglet (sessionStorage), jamais dans l'URL. */
  login: async (login: string, password: string): Promise<Session> => {
    const r = await request<Session & { token_type: string }>('POST', '/auth/login', { json: { login, password } }, false)
    const s: Session = { token: r.token, expires_at: r.expires_at, user: r.user }
    setSession(s)
    return s
  },
  logout: async (): Promise<void> => {
    try { await request<void>('POST', '/auth/logout', {}, false) } finally { setSession(null) }
  },
  health: () => get<Health>('/health'),
  commune: (slug = 'ouagadougou') => get<Commune>(`/communes/${slug}`),
  quartiers: () => get<FC<PolyGeom, QuartierProps>>('/quartiers'),
  createQuartier: (coords: [number, number][], name: string, population: number, scenarioId?: string) =>
    request<{ plans: { scenario_id: string; plan_version_id: string }[] }>('POST', '/quartiers', {
      json: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [[...coords, coords[0]]] },
              properties: { name, population, scenario_id: scenarioId } },
    }),
  reports: (q: Query) => get<FC<PointGeom, ReportProps>>('/reports', q),
  report: (id: string) => get<Feature<PointGeom, ReportProps>>(`/reports/${id}`),
  stats: () => get<Stats>('/reports/stats'),
  moderate: (id: string, status: ReportStatus, note?: string) =>
    request<Feature<PointGeom, ReportProps>>('PATCH', `/reports/${id}`, { json: { status, note, actor: 'moderateur' } }),
  revalidate: (id: string) => request<Feature<PointGeom, ReportProps>>('POST', `/reports/${id}/revalidate`),
  importFile: (file: File, dryRun: boolean) => {
    const f = new FormData()
    f.append('file', file)
    f.append('dry_run', String(dryRun))
    return request<ImportResult>('POST', '/imports', { form: f })
  },
  rollback: (batchId: string) => request<{ reverted: number }>('POST', `/imports/${batchId}/rollback`),
  dumps: (q?: Query) => get<FC<PointGeom, DumpProps>>('/dump-sites', q),
  cleaned: (id: string) => {
    const f = new FormData()
    f.append('device_id', 'tableau-de-bord')
    return request<Feature<PointGeom, DumpProps>>('POST', `/dump-sites/${id}/cleaned`, { form: f })
  },
  scenarios: () => get<Scenario[]>('/scenarios'),
  scenario: (id: string) => get<Scenario>(`/scenarios/${id}`),
  paramsSchema: () => get<ParamsSchema>('/scenarios/params-schema'),
  patchScenario: (id: string, body: { params?: Record<string, unknown>; vehicles?: { id: string; out_of_service: boolean }[] }) =>
    request<{ plan_version_id: string | null; event: string | null }>('PATCH', `/scenarios/${id}`, { json: body }),
  createScenario: (name: string, parentId: string, params: Record<string, unknown> = {}, trucks?: number) =>
    request<Scenario & { plan_version_id: string }>('POST', '/scenarios', { json: { name, parent_id: parentId, params, ...(trucks ? { trucks } : {}) } }),
  deleteScenario: (id: string) => request<void>('DELETE', `/scenarios/${id}`),
  breakdown: (sid: string, vid: string, out: boolean) =>
    request<{ plan_version_id: string }>('POST', `/scenarios/${sid}/vehicles/${vid}/breakdown`, { json: { out_of_service: out } }),
  vehicleKinds: () => get<Record<string, { label: string; capacity_t: number; cost_per_km: number; fixed_cost_day: number }>>('/scenarios/meta/vehicle-kinds'),
  addVehicle: (sid: string, kind: string) =>
    request<{ plan_version_id: string; vehicle: Vehicle }>('POST', `/scenarios/${sid}/vehicles`, { json: { kind } }),
  removeVehicle: (sid: string, vid: string) => request<{ plan_version_id: string }>('DELETE', `/scenarios/${sid}/vehicles/${vid}`),
  toLaabal: (id: string) => request<Feature<PointGeom, DumpProps>>('POST', `/dump-sites/${id}/laabal`),
  laabalAlerts: () => get<LaabalAlerts>('/dump-sites/laabal/alertes'),
  water: () => get<GeoJSON.FeatureCollection>('/eau'),
  waterDumps: (distance_m = 200) => get<WaterDumps>('/eau/depotoirs', { distance_m }),
  recompute: (sid: string) => request<{ plan_version_id: string }>('POST', `/scenarios/${sid}/recompute`, { json: { reason: 'tableau de bord' } }),
  compare: (a: string, b: string) => get<CompareResult>('/scenarios/compare', { a, b }),
  compareMany: (ids: string[]) => get<CompareMany>('/scenarios/compare-many', { ids: ids.join(',') }),
  plan: (id: string, daily = false) => get<Plan>(`/plans/${id}`, { daily }),
  points: (id: string) => get<FC<PointGeom, PointProps>>(`/plans/${id}/points`),
  routes: (id: string) => get<FC<LineGeom, RouteProps>>(`/plans/${id}/routes`),
  simulatePlanSafe: async (planId: string) => {
    const r = await request<{ sim_run_id: string }>('POST', `/plans/${planId}/simulate`, { json: { replications: 30 } })
    for (let i = 0; i < 600; i++) {
      await new Promise((ok) => setTimeout(ok, 300))
      const run = await get<{ status: string; error: string | null; metrics_summary: Record<string, { median: number; p5: number; p95: number }> }>(`/sim-runs/${r.sim_run_id}`)
      if (run.status === 'ready') return run.metrics_summary
      if (run.status === 'failed') throw new ApiError(500, 'Simulation', run.error ?? 'Échec')
    }
    throw new ApiError(504, 'Simulation', 'Simulation trop longue')
  },
  audit: (limit = 100) => get<AuditEntry[]>('/audit', { limit }),
  rules: () => get<ValidationRules>('/validation/rules'),
  exportUrl: (fmt: 'geojson' | 'csv' | 'osm') => `/api/export/${fmt}`,
}
