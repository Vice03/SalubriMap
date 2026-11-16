// SPDX-License-Identifier: AGPL-3.0-or-later
import { CloudRain, Copy, PenLine, RefreshCw, SlidersHorizontal, Sun } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { ParamSchemaProp } from '../api/types'
import { FleetPanel } from '../components/dashboard/FleetPanel'
import { MapView, type Layers } from '../components/map/MapView'
import { LineChart } from '../components/ui/Charts'
import { fcfa, km, num, pct, tonnes, weekly } from '../lib/format'
import { useApi, useApp } from '../state/app'

const MAIN = ['budget_fcfa_month', 'subscription_rate', 'pickup_frequency_per_week', 'precollector_frequency_per_week',
  'collection_point_capacity_t', 'cleanup_capacity_t_day', 'laabal_operations_per_week', 'laabal_deterrence', 'waste_kg_per_person_day', 'population_factor', 'walk_distance_max_m']
const HIDDEN = ['season', 'active_quartier_ids']
const LAYERS: Layers = { quartiers: true, dumps: false, reports: false, points: true, routes: true, trucks: true }

function Field({ name, prop, value, onChange }: { name: string; prop: ParamSchemaProp; value: unknown; onChange: (v: unknown) => void }) {
  const isInt = prop.type === 'integer'
  const isPct = name === 'subscription_rate' || name === 'truck_breakdown_rate_per_day'
  const shown = typeof value === 'number' ? (isPct ? Math.round(value * 1000) / 10 : value) : value
  return (
    <div className="field">
      <label htmlFor={name}>{prop.label ?? name}{isPct ? ' (%)' : ''}</label>
      <input id={name} type="number" step={isInt ? 1 : 'any'} value={String(shown ?? '')}
        min={prop.minimum != null ? (isPct ? prop.minimum * 100 : prop.minimum) : undefined}
        max={prop.maximum != null ? (isPct ? prop.maximum * 100 : prop.maximum) : undefined}
        onChange={(e) => {
          const raw = e.target.value === '' ? null : Number(e.target.value)
          onChange(raw == null ? null : isPct ? raw / 100 : isInt ? Math.round(raw) : raw)
        }} />
    </div>
  )
}

export function ScenarioPage() {
  const { scenario, track, toast, reloadScenarios, setScenarioId } = useApp()
  const planId = scenario?.latest_ready_plan_id ?? null
  const { data: schema } = useApi(() => api.paramsSchema(), [])
  const { data: commune } = useApi(() => api.commune(), [])
  const { data: quartiers } = useApi(() => api.quartiers(), [])
  const { data: plan } = useApi(() => (planId ? api.plan(planId, true) : Promise.resolve(null)), [planId])
  const { data: points } = useApi(() => (planId ? api.points(planId) : Promise.resolve(null)), [planId])
  const { data: routes } = useApi(() => (planId ? api.routes(planId) : Promise.resolve(null)), [planId])
  const [draft, setDraft] = useState<Record<string, unknown>>({})
  const [advanced, setAdvanced] = useState(false)
  const [drawing, setDrawing] = useState(false)
  const [poly, setPoly] = useState<[number, number][]>([])
  const [qName, setQName] = useState('Nouveau secteur')
  const [qPop, setQPop] = useState(45000)
  const [reps, setReps] = useState<Record<string, { median: number; p10: number; p90: number }> | null>(null)

  useEffect(() => { setDraft({}); setReps(null) }, [scenario?.id, planId])
  const params = useMemo(() => ({ ...(scenario?.params ?? {}), ...draft }), [scenario, draft])
  const changed = Object.keys(draft).filter((k) => draft[k] !== scenario?.params[k] && draft[k] != null)

  const apply = async (body: Record<string, unknown>, label: string) => {
    if (!scenario) return
    try {
      const r = await api.patchScenario(scenario.id, { params: body })
      setDraft({})
      if (r.plan_version_id) track(r.plan_version_id, r.event ?? label)
      void reloadScenarios()
    } catch (e) { toast('error', (e as Error).message) }
  }
  const sim = plan?.summary.sim ?? {}
  const daily = plan?.summary.sim_daily ?? {}
  const s = plan?.summary
  const props = schema?.properties ?? {}
  const others = Object.keys(props).filter((k) => !MAIN.includes(k) && !HIDDEN.includes(k))

  const runReplications = async () => {
    if (!planId) return
    const r = await api.simulatePlanSafe(planId)
    setReps(r)
  }

  return (
    <div className="content">
      <div className="grid row-map">
        <div className="card">
          <div className="card-head">
            <SlidersHorizontal color="#0f2b55" /><h2>Scénario « {scenario?.name ?? '…'} »</h2><span className="spacer" />
            <button className="pill-btn" onClick={async () => {
              if (!scenario) return
              const name = window.prompt('Nom du nouveau scénario', `${scenario.name} (copie)`)
              if (!name) return
              const sc = await api.createScenario(name, scenario.id)
              await reloadScenarios(); setScenarioId(sc.id); track(sc.plan_version_id, 'manual')
            }}><Copy size={14} />Dupliquer</button>
            <button className="pill-btn" onClick={async () => { if (scenario) { const r = await api.recompute(scenario.id); track(r.plan_version_id, 'manual') } }}><RefreshCw size={14} />Recalcul complet</button>
          </div>
          <div className="season" style={{ marginBottom: 16 }}>
            <button className={params.season === 'dry' ? 'on' : ''} onClick={() => params.season !== 'dry' && void apply({ season: 'dry' }, 'season_changed')}><Sun color="#f59e0b" size={28} />Saison sèche</button>
            <button className={params.season === 'rain' ? 'on' : ''} onClick={() => params.season !== 'rain' && void apply({ season: 'rain' }, 'season_changed')}><CloudRain color="#2563eb" size={28} />Saison des pluies</button>
          </div>
          <div className="form-grid">
            {MAIN.filter((k) => props[k]).map((k) => <Field key={k} name={k} prop={props[k]} value={params[k]} onChange={(v) => setDraft({ ...draft, [k]: v })} />)}
          </div>
          <button className="link" style={{ margin: '12px 0' }} onClick={() => setAdvanced(!advanced)}>{advanced ? 'Masquer' : 'Afficher'} les paramètres avancés</button>
          {advanced && <div className="form-grid">{others.map((k) => <Field key={k} name={k} prop={props[k]} value={params[k]} onChange={(v) => setDraft({ ...draft, [k]: v })} />)}</div>}
          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <button className="btn primary" disabled={!changed.length} onClick={() => void apply(Object.fromEntries(changed.map((k) => [k, draft[k]])), 'manual')}>
              Appliquer {changed.length ? `(${changed.length})` : ''}
            </button>
            {changed.length > 0 && <button className="btn ghost" onClick={() => setDraft({})}>Annuler</button>}
          </div>
        </div>
        <FleetPanel scenario={scenario} routes={routes} compact />
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Plan de collecte</h2><span className="spacer" />
          {plan && <span className="muted">version {plan.version} · {plan.distance_mode === 'osrm' ? 'réseau routier' : 'distances approximatives'} · solveur {s?.solver}</span>}
          <button className={`pill-btn ${drawing ? 'on' : ''}`} onClick={() => { setDrawing(!drawing); setPoly([]) }}><PenLine size={14} />Nouveau quartier</button>
        </div>
        <div className="map-wrap" style={{ height: 420 }}>
          <MapView commune={commune} quartiers={quartiers} points={points} routes={routes} layers={LAYERS} fitPlan
            drawing={drawing} draft={poly} onDraftPoint={(p) => setPoly((x) => [...x, p])} />
          {drawing && (
            <div className="draw-box">
              <b>Dessiner le nouveau quartier</b>
              <span className="muted">Cliquer sur la carte pour placer les sommets ({poly.length} placé{poly.length > 1 ? 's' : ''}).</span>
              <input value={qName} onChange={(e) => setQName(e.target.value)} aria-label="Nom du quartier" />
              <input type="number" value={qPop} onChange={(e) => setQPop(Number(e.target.value))} aria-label="Population" />
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn ghost" onClick={() => setPoly([])}>Effacer</button>
                <button className="btn primary" disabled={poly.length < 3 || !scenario} onClick={async () => {
                  try {
                    const r = await api.createQuartier(poly, qName, qPop, scenario?.id)
                    setDrawing(false); setPoly([])
                    const mine = r.plans.find((x) => x.scenario_id === scenario?.id) ?? r.plans[0]
                    if (mine) track(mine.plan_version_id, 'zone_changed')
                  } catch (e) { toast('error', (e as Error).message) }
                }}>Valider</button>
              </div>
            </div>
          )}
        </div>
        {s?.diff && <div style={{ marginTop: 12, fontWeight: 600 }}>Dernier changement : {s.diff.text}</div>}
        {!!s?.unserved_points && s.points ? (
          <div className="fleet-gap">
            <b>Flotte insuffisante pour cette zone.</b> Avec {s.vehicles_available} camion(s), {pct(1 - s.unserved_points / s.points)} des points
            sont desservis{s.trucks_needed ? <> : il en faudrait environ <b>{s.trucks_needed}</b> (même capacité, 2 rotations par jour)</> : null}.
            Ajoutez des camions dans le panneau Flotte ou réduisez la zone active.
          </div>
        ) : null}
        <div className="grid kpis" style={{ marginTop: 14 }}>
          {[
            ['Points de regroupement', num(s?.points)], ['Tournées', num(s?.routes)], ['Distance par jour de collecte', km(s?.km_day)],
            ['Coût d\'une journée de collecte', fcfa(s?.cost_day_fcfa)], ['Points non desservis', num(s?.unserved_points)],
            ['Déchets à collecter', `${tonnes(s?.demand_t_week)}/semaine`],
          ].map(([l, v]) => <div key={l} className="card" style={{ boxShadow: 'none', background: '#f8fafd' }}><div className="muted">{l}</div><div className="kpi-value" style={{ fontSize: 24 }}>{v}</div></div>)}
        </div>
      </div>

      <div className="grid row-3">
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-head"><h2>Simulation sur {num(Number(params.horizon_days ?? 90))} jours</h2><span className="spacer" />
            <button className="pill-btn" onClick={() => void runReplications()}>5 réplications</button></div>
          <LineChart yLabel="tonnes par semaine" labels={weekly(daily.truck_collected_t).map((_, i) => `S${i + 1}`)} series={[
            { name: 'Collecté', color: '#2563eb', values: weekly(daily.truck_collected_t), unit: ' t' },
            { name: 'Parti en dépôt sauvage', color: '#dc2626', values: weekly(daily.wild_new_t), unit: ' t' },
            { name: 'Nettoyé par la mairie', color: '#16a34a', values: weekly(daily.cleanup_t), unit: ' t' },
            { name: 'Évacué par les riverains après contrôle Laabal', color: '#7c3aed', values: weekly(daily.laabal_cleared_t), unit: ' t' },
          ]} />
        </div>
        <div className="card">
          <div className="card-head"><h2>Indicateurs simulés</h2></div>
          {[
            ['Tonnage collecté', tonnes(sim.collected_t, 0), 'collected_t'],
            ['Parti en dépôt sauvage', tonnes(sim.wild_dump_t, 0), 'wild_dump_t'],
            ['Dépotoirs actifs (moyenne)', num(sim.wild_dumps_active_mean, 1), 'wild_dumps_active_mean'],
            ['Débordements (points × jours)', num(sim.overflow_point_days), 'overflow_point_days'],
            ['Coût par tonne', fcfa(sim.cost_per_t), 'cost_per_t'],
            ['Couverture de la population', pct(sim.coverage_rate), 'coverage_rate'],
            ['Taux d\'abonnement final', pct(sim.subscription_rate_final), 'subscription_rate_final'],
            ['Contrôles Laabal (îlots inspectés)', num(sim.laabal_controls), 'laabal_controls'],
            ['Délai moyen de nettoyage', `${num(sim.mean_cleanup_delay_days, 1)} j`, 'mean_cleanup_delay_days'],
          ].map(([l, v, k]) => (
            <div key={k} className="list-item"><span style={{ flex: 1 }}>{l}</span><b>{v}</b>
              {reps?.[k] && <span className="muted" style={{ marginLeft: 8 }}>[{num(reps[k].p10, 1)} – {num(reps[k].p90, 1)}]</span>}</div>
          ))}
          {reps && <div className="muted">Entre crochets : intervalle p10–p90 sur 5 réplications.</div>}
        </div>
      </div>
    </div>
  )
}
