// SPDX-License-Identifier: AGPL-3.0-or-later
import type {
  AuditEntry, Commune, CompareResult, DumpProps, FC, Feature, Health, ImportResult, LineGeom, ParamsSchema,
  Plan, PointGeom, PointProps, PolyGeom, QuartierProps, ReportProps, ReportStatus, RouteProps, Scenario, Stats,
  ValidationRules, Vehicle,
} from './types'

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

const TOKEN_KEY = 'salubri_mairie_code'
const readToken = () => { try { return localStorage.getItem(TOKEN_KEY) ?? '' } catch { return '' } }
const saveToken = (t: string) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* stockage indisponible */ } }

/** Les écritures (modération, imports, scénarios, flotte) exigent le code d'accès mairie. */
async function request<T>(method: string, path: string, opts: { query?: Query; json?: unknown; form?: FormData } = {}, retry = true): Promise<T> {
  const init: RequestInit = { method, headers: method === 'GET' ? {} : { 'X-Salubri-Token': readToken() } }
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
  if (res.status === 401 && retry) {
    const code = window.prompt("Code d'accès mairie (modération, imports, scénarios) :")
    if (code) { saveToken(code.trim()); return request<T>(method, path, opts, false) }
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
  createScenario: (name: string, parentId: string, params: Record<string, unknown> = {}) =>
    request<Scenario & { plan_version_id: string }>('POST', '/scenarios', { json: { name, parent_id: parentId, params } }),
  deleteScenario: (id: string) => request<void>('DELETE', `/scenarios/${id}`),
  breakdown: (sid: string, vid: string, out: boolean) =>
    request<{ plan_version_id: string }>('POST', `/scenarios/${sid}/vehicles/${vid}/breakdown`, { json: { out_of_service: out } }),
  vehicleKinds: () => get<Record<string, { label: string; capacity_t: number; cost_per_km: number; fixed_cost_day: number }>>('/scenarios/meta/vehicle-kinds'),
  addVehicle: (sid: string, kind: string) =>
    request<{ plan_version_id: string; vehicle: Vehicle }>('POST', `/scenarios/${sid}/vehicles`, { json: { kind } }),
  removeVehicle: (sid: string, vid: string) => request<{ plan_version_id: string }>('DELETE', `/scenarios/${sid}/vehicles/${vid}`),
  toLaabal: (id: string) => request<Feature<PointGeom, DumpProps>>('POST', `/dump-sites/${id}/laabal`),
  recompute: (sid: string) => request<{ plan_version_id: string }>('POST', `/scenarios/${sid}/recompute`, { json: { reason: 'tableau de bord' } }),
  compare: (a: string, b: string) => get<CompareResult>('/scenarios/compare', { a, b }),
  plan: (id: string, daily = false) => get<Plan>(`/plans/${id}`, { daily }),
  points: (id: string) => get<FC<PointGeom, PointProps>>(`/plans/${id}/points`),
  routes: (id: string) => get<FC<LineGeom, RouteProps>>(`/plans/${id}/routes`),
  simulatePlanSafe: async (planId: string) => {
    const r = await request<{ sim_run_id: string }>('POST', `/plans/${planId}/simulate`, { json: { replications: 5 } })
    for (let i = 0; i < 100; i++) {
      await new Promise((ok) => setTimeout(ok, 300))
      const run = await get<{ status: string; error: string | null; metrics_summary: Record<string, { median: number; p10: number; p90: number }> }>(`/sim-runs/${r.sim_run_id}`)
      if (run.status === 'ready') return run.metrics_summary
      if (run.status === 'failed') throw new ApiError(500, 'Simulation', run.error ?? 'Échec')
    }
    throw new ApiError(504, 'Simulation', 'Simulation trop longue')
  },
  audit: (limit = 100) => get<AuditEntry[]>('/audit', { limit }),
  rules: () => get<ValidationRules>('/validation/rules'),
  exportUrl: (fmt: 'geojson' | 'csv' | 'osm') => `/api/export/${fmt}`,
}
