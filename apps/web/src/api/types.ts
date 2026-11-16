// SPDX-License-Identifier: AGPL-3.0-or-later
export type WasteType = 'household' | 'plastic' | 'rubble' | 'organic' | 'medical' | 'mixed' | 'other'
export type VolumeClass = 'bag' | 'wheelbarrow' | 'cart' | 'truck' | 'more'
export type ReportStatus = 'pending' | 'probable' | 'verified' | 'to_review' | 'rejected' | 'cleaned'
export type DumpStatus = 'active' | 'recurring' | 'cleaned'
export type PlanStatus = 'pending' | 'running' | 'ready' | 'failed' | 'superseded'

export type Position = [number, number]
export interface Feature<G, P> { type: 'Feature'; id?: string; geometry: G; properties: P }
export interface FC<G, P> { type: 'FeatureCollection'; features: Feature<G, P>[]; total?: number }
export interface PointGeom { type: 'Point'; coordinates: Position }
export interface LineGeom { type: 'LineString'; coordinates: Position[] }
export interface PolyGeom { type: 'Polygon' | 'MultiPolygon'; coordinates: Position[][] | Position[][][] }

export interface RuleHit { rule: string; delta: number; detail: string; reject?: boolean }

export interface ReportProps {
  id: string; status: ReportStatus; score: number; rule_hits: RuleHit[]
  waste_type: WasteType; volume_class: VolumeClass; comment: string | null
  reported_at: string; received_at: string; gps_accuracy_m: number | null
  device_id: string | null; external_id: string | null; duplicate_of: string | null
  dump_site_id: string | null; quartier_id: string | null; import_batch_id: string | null
  photo_url: string | null; forced_status: boolean; moderated_by: string | null; moderated_at: string | null
  related?: { id: string; status: ReportStatus; score: number; relation: 'original' | 'duplicate' }[]
  dump_site?: { id: string; status: DumpStatus; n_reports: number }
}

export interface DumpProps {
  id: string; status: DumpStatus; waste_type: WasteType; volume_est_m3: number; n_reports: number
  first_reported_at: string; last_reported_at: string; near_water: boolean; priority: number
  confidence: number; osm_id: number | null
  site_kind?: 'sauvage' | 'encadree' | 'autre'; ref?: string | null
}

export interface QuartierProps {
  id: string; name: string; arrondissement: number | null; population: number; active: boolean
  source: string; n_ilots: number
}

export interface PointProps {
  id: string; key: string; label: string; capacity_t: number; demand_t_week: number
  fill_ratio_per_pickup: number | null; n_ilots: number; frozen: boolean; time_window: [number, number]
  unserved: boolean
}

export interface RouteStop { seq: number; point_key: string; point_id: string; arrival_min: number; load_t_after: number }
export interface RouteProps {
  id: string; vehicle_id: string; vehicle_label: string; vehicle_kind: string; capacity_t: number
  rotation: number; distance_km: number; duration_min: number; load_t: number; cost_fcfa: number; stops: RouteStop[]
}

export interface StageRecord { stage: string; name: string; duration_ms: number; cache_hit: boolean }
export interface PlanDiff {
  first_version: boolean; points_added: number; points_removed: number; points_moved: number
  routes_changed: number; km_delta: number; km_delta_pct: number | null; cost_delta: number
  unserved_delta: number; text: string
}
export interface SimSummary { [k: string]: number }
export interface PlanSummary {
  ilots?: number; population?: number; demand_t_week?: number; points?: number; routes?: number
  vehicles_available?: number; km_day?: number; cost_day_fcfa?: number; unserved_points?: number
  unserved_t_per_pickup?: number; distance_mode?: string; solver?: string; duration_ms?: number
  diff?: PlanDiff; sim?: SimSummary; sim_daily?: Record<string, number[]>
}
export interface Plan {
  id: string; scenario_id: string; version: number; status: PlanStatus; event: string
  distance_mode: 'osrm' | 'approx'; stages: StageRecord[]; summary: PlanSummary; error: string | null
  created_at: string; started_at: string | null; finished_at: string | null
}

export interface Vehicle {
  id: string; label: string; kind: string; capacity_t: number; cost_per_km: number; fixed_cost_day: number
  out_of_service: boolean; shift_start: number; shift_end: number
}
export interface Scenario {
  id: string; name: string; parent_id: string | null; is_baseline: boolean; params: Record<string, unknown>
  vehicles: Vehicle[]; latest_ready_plan_id: string | null; latest_plan_id: string | null
  latest_plan_status: PlanStatus | null; updated_at: string
}

export interface Stats {
  total: number; by_status: Partial<Record<ReportStatus, number>>; by_type: Partial<Record<WasteType, number>>
  by_rule: Record<string, number>; dump_sites: Partial<Record<DumpStatus, number>>
}

export interface Commune { id: string; slug: string; name: string; bbox: [number, number, number, number]; center: Position; depot: Position }

export interface ImportRow {
  row: number; status: 'accepted' | 'rejected'; errors: string[]; warnings: string[]; report_id: string | null
  external_id: string | null; score: number | null; report_status: ReportStatus | null; rule_hits: RuleHit[]
}
export interface ImportResult {
  batch_id: string | null; dry_run: boolean; format: string; rows_total: number; accepted: number
  rejected: number; report: ImportRow[]
}

export interface AuditEntry {
  id: string; actor: string; action: string; entity: string; entity_id: string | null
  before: Record<string, unknown> | null; after: Record<string, unknown> | null; at: string
}

export interface ParamSchemaProp {
  type?: string; title?: string; label?: string; default?: unknown; minimum?: number; maximum?: number
  exclusiveMinimum?: number; enum?: string[]; event?: string | null; anyOf?: { type?: string }[]
}
export interface ParamsSchema { properties: Record<string, ParamSchemaProp> }

export interface CompareSide { scenario_id: string; name: string; plan_id: string | null; summary: PlanSummary; wild_dumps_daily: number[] }
export interface CompareResult {
  a: CompareSide; b: CompareSide
  delta: Record<string, { a: number; b: number; value: number; pct: number | null }>
  better_when_lower: string[]
}

export interface Health { status: string; db: string; osrm: string; version: string }
export interface ValidationRules { rules: { code: string; title: string; description: string; penalty: string }[] }
