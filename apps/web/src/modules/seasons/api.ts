// SPDX-License-Identifier: AGPL-3.0-or-later
import { authHeaders } from '../../api/session'

async function call<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() }
  let payload: BodyInit | undefined
  if (form) payload = form
  else if (body !== undefined) { payload = JSON.stringify(body); headers['Content-Type'] = 'application/json' }
  const r = await fetch(`/api/roads${path}`, { method, headers, body: payload })
  const b = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(typeof b.detail === 'string' ? b.detail : `Erreur ${r.status}`)
  return b as T
}

export interface Moved { point: string; distance_m?: number; raison: string; menages?: number }
export interface PlanSeason { periode: string; routes_impraticables?: number; points_deplaces: Moved[]; points_inaccessibles: Moved[] }
export interface ImportResult { accepted: number; rejected: number; rows: number; batch_id?: string; colonnes: Record<string, string | null>; report: { row: number; status: string; errors?: string[] }[] }

export const seasonsApi = {
  roads: (period: string) => call<GeoJSON.FeatureCollection>('GET', `?period=${encodeURIComponent(period)}`),
  near: (lon: number, lat: number) => call<{ road_id: string; distance_m: number; highway: string }>('GET', `/near?lon=${lon}&lat=${lat}`),
  set: (roadId: string, period: string, passable: boolean) => call('PUT', `/${roadId}/conditions/${period}`, { passable }),
  plan: (planId: string) => call<PlanSeason>('GET', `/plans/${planId}`),
  importFile: (file: File, dry: boolean) => { const f = new FormData(); f.append('file', file); f.append('dry_run', String(dry)); return call<ImportResult>('POST', '/conditions/import', undefined, f) },
  undo: (batch: string) => call('DELETE', `/conditions/import/${batch}`),
}
