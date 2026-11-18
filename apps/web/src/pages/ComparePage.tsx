// SPDX-License-Identifier: AGPL-3.0-or-later
import { ArrowLeftRight, FlaskConical, Map as MapIcon, Plus, Sparkles, Trophy, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { can, useSession } from '../api/session'
import type { CompareMany } from '../api/types'
import { MapView, type Layers } from '../components/map/MapView'
import { LineChart } from '../components/ui/Charts'
import { RoleButton } from '../components/ui/RoleButton'
import { num } from '../lib/format'
import { askAssistant } from '../modules/assistant/bus'
import { useModules } from '../modules/useModules'
import { useApi, useApp } from '../state/app'

export const LABELS: Record<string, string> = {
  points: 'Points de regroupement', routes: 'Tournées', km_day: 'km par jour de collecte', cost_day_fcfa: 'Coût d\'une journée (FCFA)',
  unserved_points: 'Points non desservis', demand_t_week: 'Déchets à collecter (t/semaine)',
  'sim.collected_t': 'Tonnage collecté (t)', 'sim.wild_dump_t': 'Parti en dépôt sauvage (t)',
  'sim.wild_dumps_active_final': 'Dépotoirs actifs à la fin', 'sim.wild_dumps_active_mean': 'Dépotoirs actifs (moyenne)',
  'sim.overflow_point_days': 'Débordements (points × jours)', 'sim.cost_total_fcfa': 'Coût total (FCFA)',
  'sim.cost_per_t': 'Coût par tonne (FCFA)', 'sim.coverage_rate': 'Couverture', 'sim.subscription_rate_final': 'Taux d\'abonnement final',
  'sim.mean_cleanup_delay_days': 'Délai moyen de nettoyage (j)',
  'couts.total_mois_fcfa': 'Coût estimé par mois (FCFA)', 'couts.cout_par_tonne_fcfa': 'Coût estimé par tonne (FCFA)',
  'couts.carburant': 'Gasoil par mois (FCFA)', 'couts.equipages': 'Équipages par mois (FCFA)', 'couts.km_mois': 'km par mois',
  'couts.camions_flotte': 'Camions dans la flotte',
}

/** Implantations de la ville entière : chaque variante change la façon de couvrir la ville (marche, bacs, rythme,
 *  horaires). Toutes partent de la référence, sur toute la ville, avec la flotte choisie. */
interface Layout { name: string; params: Record<string, unknown> }
const LAYOUTS: Layout[] = [
  { name: 'Ville · implantation de base', params: {} },
  { name: 'Ville · bacs à 200 m', params: { walk_distance_max_m: 200 } },
  { name: 'Ville · bacs à 400 m', params: { walk_distance_max_m: 400 } },
  { name: 'Ville · gros bacs (5 t)', params: { collection_point_capacity_t: 5 } },
  { name: 'Ville · 3 enlèvements/semaine', params: { pickup_frequency_per_week: 3, pickup_frequency_max_per_week: 3 } },
  { name: 'Ville · équipes 6 h – 14 h', params: { work_start_h: 6, work_end_h: 14, break_min: 30 } },
]
/** Couleurs des cas, toujours dans cet ordre (le cas n garde sa couleur quand on en ajoute un autre). */
export const CASE_COLORS = ['#1565c0', '#ef6c00', '#2e7d32', '#8e24aa', '#c62828', '#00838f', '#6d4c41', '#546e7a']

interface Recipe { name: string; breakdown: number; season: '' | 'dry' | 'rain'; subscriptionPts: number; budgetPct: number; params?: Record<string, unknown>; city?: boolean; trucks?: number }
const PRESETS: Recipe[] = [
  { name: '2 camions en panne', breakdown: 2, season: '', subscriptionPts: 0, budgetPct: 0 },
  { name: 'Saison des pluies', breakdown: 0, season: 'rain', subscriptionPts: 0, budgetPct: 0 },
  { name: 'Abonnement +20 pts', breakdown: 0, season: '', subscriptionPts: 20, budgetPct: 0 },
  { name: 'Budget −30 %', breakdown: 0, season: '', subscriptionPts: 0, budgetPct: -30 },
]

const isRate = (k: string) => k.endsWith('rate') || k.endsWith('rate_final')
const fmt = (k: string, x: number) => (isRate(k) ? `${num(x * 100, 1)} %` : num(x, Math.abs(x) < 10 ? 1 : 0))

export function ComparePage() {
  const { scenarios, scenario, reloadScenarios, track, toast, refreshKey } = useApp()
  const session = useSession()
  const modules = useModules()
  const [ids, setIds] = useState<string[]>([])
  const [custom, setCustom] = useState<Recipe>({ name: 'Mon cas', breakdown: 0, season: '', subscriptionPts: 0, budgetPct: 0, params: {}, city: false })
  const [layoutPick, setLayoutPick] = useState<string[]>(LAYOUTS.slice(0, 4).map((l) => l.name))
  const [fleet, setFleet] = useState<number>(0)
  const [launching, setLaunching] = useState(false)
  const [showCustom, setShowCustom] = useState(false)
  const [tick, setTick] = useState(0)

  // Par défaut : le scénario affiché et les cas simulés à partir de lui (même zone, donc comparables)
  useEffect(() => {
    if (ids.length || !scenario) return
    setIds([scenario.id, ...scenarios.filter((s) => s.parent_id === scenario.id).map((s) => s.id)].slice(0, 8))
  }, [scenarios, scenario, ids.length])
  // Un cas supprimé disparaît de la sélection
  useEffect(() => { setIds((x) => x.filter((id) => scenarios.some((s) => s.id === id))) }, [scenarios])

  const { data, loading } = useApi(() => (ids.length >= 2 ? api.compareMany(ids) : Promise.resolve(null)), [ids.join(','), refreshKey, tick])
  // Un cas encore en calcul : on relit toutes les 4 s
  const pending = useMemo(() => ids.some((id) => !scenarios.find((s) => s.id === id)?.latest_ready_plan_id || scenarios.find((s) => s.id === id)?.latest_plan_status === 'running' || scenarios.find((s) => s.id === id)?.latest_plan_status === 'pending'), [ids, scenarios])
  useEffect(() => {
    if (!pending) return
    const t = setInterval(() => { void reloadScenarios(); setTick((x) => x + 1) }, 4000)
    return () => clearInterval(t)
  }, [pending, reloadScenarios])

  const toggle = (id: string) => setIds((x) => (x.includes(id) ? x.filter((y) => y !== id) : x.length >= 8 ? x : [...x, id]))
  const makeRef = (id: string) => setIds((x) => [id, ...x.filter((y) => y !== id)])

  const simulate = async (r: Recipe) => {
    const base = scenarios.find((s) => s.id === ids[0]) ?? scenario
    if (!base) return
    try {
      const params: Record<string, unknown> = { ...(r.params ?? {}) }
      if (r.city) params.active_quartier_ids = null  // toute la ville
      if (r.season) params.season = r.season
      if (r.subscriptionPts) params.subscription_rate = Math.max(0, Math.min(1, Number(base.params.subscription_rate) + r.subscriptionPts / 100))
      if (r.budgetPct) params.budget_fcfa_month = Math.round(Number(base.params.budget_fcfa_month) * (1 + r.budgetPct / 100))
      const sc = await api.createScenario(r.city ? r.name : `${base.name} — ${r.name}`, base.id, params, r.trucks || undefined)
      let planId = sc.plan_version_id
      if (r.breakdown > 0) {
        const vs = sc.vehicles.filter((v) => !v.out_of_service).slice(-r.breakdown)
        const res = await api.patchScenario(sc.id, { vehicles: vs.map((v) => ({ id: v.id, out_of_service: true })) })
        if (res.plan_version_id) planId = res.plan_version_id
      }
      await reloadScenarios()
      setIds((x) => (x.length >= 8 ? x : [...x, sc.id]))
      track(planId, r.name)
    } catch (e) { toast('error', (e as Error).message) }
  }
  // Flotte proposée pour la ville entière : celle qu'estime le plan de la référence, sinon 30 camions
  const ref = scenarios.find((s) => s.id === ids[0]) ?? scenario
  const suggested = 30
  const launchLayouts = async () => {
    setLaunching(true)
    for (const l of LAYOUTS.filter((x) => layoutPick.includes(x.name))) {
      await simulate({ name: l.name, breakdown: 0, season: '', subscriptionPts: 0, budgetPct: 0, params: l.params, city: true, trucks: fleet || suggested })
    }
    setLaunching(false)
  }
  const remove = async (id: string) => {
    try { await api.deleteScenario(id); await reloadScenarios() } catch (e) { toast('error', (e as Error).message) }
  }

  const analyse = () => {
    if (!data) return
    const names = data.scenarios.map((s) => `« ${s.name} »`).join(', ')
    askAssistant(`Analyse la comparaison des scénarios ${names} (le premier est la référence). Lequel recommandes-tu à la mairie, pour quelles raisons chiffrées, et quels sont les risques ?`)
  }

  const colorOf = (id: string) => CASE_COLORS[Math.max(0, scenarios.findIndex((s) => s.id === id)) % CASE_COLORS.length]
  const admin = !!session && can('admin', session)

  return (
    <div className="content">
      <div className="card">
        <div className="card-head">
          <span className="head-icon" style={{ background: 'var(--grad-blue)' }}><ArrowLeftRight size={18} color="#fff" /></span>
          <h2>Comparer plusieurs cas</h2>
          <span className="spacer" />
          <span className="muted">{ids.length} cas sélectionné(s) · le premier sert de référence</span>
        </div>
        <div className="case-chips">
          {scenarios.map((s) => {
            const on = ids.includes(s.id)
            const ref = ids[0] === s.id
            return (
              <span key={s.id} className={`case-chip${on ? ' on' : ''}`} style={{ ['--c' as string]: colorOf(s.id) }}>
                <button className="case-main" onClick={() => toggle(s.id)} aria-pressed={on} title={on ? 'Retirer de la comparaison' : 'Ajouter à la comparaison'}>
                  <span className="case-dot" />{s.name}
                  {s.latest_plan_status && s.latest_plan_status !== 'ready' && s.latest_plan_status !== 'failed' && <em> · calcul…</em>}
                </button>
                {on && !ref && <button className="case-ref" onClick={() => makeRef(s.id)} title="En faire la référence">réf.</button>}
                {ref && <span className="case-badge">référence</span>}
                {admin && !s.is_baseline && <button className="case-x" onClick={() => void remove(s.id)} aria-label={`Supprimer ${s.name}`}><X size={13} /></button>}
              </span>
            )
          })}
        </div>
        <div className="sim-row">
          <span className="sim-title"><FlaskConical size={16} /> Simuler un nouveau cas à partir de la référence :</span>
          {PRESETS.map((p) => <RoleButton need="admin" key={p.name} className="pill-btn" onClick={() => void simulate(p)}>{p.name}</RoleButton>)}
          <RoleButton need="admin" className="pill-btn accent" onClick={() => setShowCustom((x) => !x)}><Plus size={14} /> Cas sur mesure</RoleButton>
        </div>
        <div className="layouts">
          <div className="sim-title"><MapIcon size={16} /> Comparer des implantations de la <b>ville entière</b> :</div>
          <div className="layout-picks">
            {LAYOUTS.map((l) => (
              <label key={l.name} className={`layout-pick${layoutPick.includes(l.name) ? ' on' : ''}`}>
                <input type="checkbox" checked={layoutPick.includes(l.name)} onChange={(e) => setLayoutPick((x) => e.target.checked ? [...x, l.name] : x.filter((y) => y !== l.name))} />
                {l.name.replace('Ville · ', '')}
              </label>
            ))}
          </div>
          <div className="layout-go">
            <label>Camions<input type="number" min={1} max={200} value={fleet || suggested} onChange={(e) => setFleet(Math.max(1, Number(e.target.value) || 1))} /></label>
            <RoleButton need="admin" className="btn-primary" disabled={!layoutPick.length || launching || !ref} onClick={() => void launchLayouts()}>
              {launching ? 'Lancement…' : `Calculer ${layoutPick.length} implantation(s)`}
            </RoleButton>
            <span className="muted">Chaque implantation se calcule en arrière-plan (environ 1 min sur la ville entière) ; ses résultats arrivent ici tout seuls.</span>
          </div>
        </div>
        {showCustom && (
          <div className="custom-case">
            <label>Nom<input value={custom.name} onChange={(e) => setCustom({ ...custom, name: e.target.value })} /></label>
            <label>Camions en panne<input type="number" min={0} max={8} value={custom.breakdown} onChange={(e) => setCustom({ ...custom, breakdown: Math.max(0, Number(e.target.value) || 0) })} /></label>
            <label>Saison<select value={custom.season} onChange={(e) => setCustom({ ...custom, season: e.target.value as Recipe['season'] })}>
              <option value="">comme la référence</option><option value="dry">sèche</option><option value="rain">des pluies</option></select></label>
            <label>Abonnement (± points)<input type="number" min={-50} max={50} value={custom.subscriptionPts} onChange={(e) => setCustom({ ...custom, subscriptionPts: Number(e.target.value) || 0 })} /></label>
            <label>Budget (± %)<input type="number" min={-80} max={200} value={custom.budgetPct} onChange={(e) => setCustom({ ...custom, budgetPct: Number(e.target.value) || 0 })} /></label>
            <label>Ville entière<select value={custom.city ? '1' : ''} onChange={(e) => setCustom({ ...custom, city: !!e.target.value })}><option value="">non (zone de la référence)</option><option value="1">oui</option></select></label>
            <label>Camions (flotte)<input type="number" min={0} max={200} placeholder="comme la référence" value={custom.trucks || ''} onChange={(e) => setCustom({ ...custom, trucks: Number(e.target.value) || undefined })} /></label>
            {CUSTOM_PARAMS.map(([k, label, step]) => (
              <label key={k}>{label}<input type="number" step={step} placeholder={String(ref?.params[k] ?? '')} value={custom.params?.[k] == null ? '' : String(custom.params[k])}
                onChange={(e) => setCustom({ ...custom, params: { ...(custom.params ?? {}), [k]: e.target.value === '' ? undefined : Number(e.target.value) } })} /></label>
            ))}
            <button className="btn-primary" onClick={() => { void simulate(custom); setShowCustom(false) }}>Simuler ce cas</button>
          </div>
        )}
      </div>

      {data && <Ranking data={data} onAnalyse={analyse} assistant={modules.assistant} />}

      {data && (
        <>
          <div className="card" style={{ overflowX: 'auto' }}>
            <table className="table compare-table">
              <thead>
                <tr><th>Indicateur</th>{data.scenarios.map((s, i) => (
                  <th key={s.scenario_id}><span className="case-dot" style={{ background: colorOf(s.scenario_id) }} /> {i === 0 ? 'Réf. · ' : ''}{s.name}{!s.plan_id && <em className="muted"> (en calcul)</em>}</th>
                ))}</tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.key}>
                    <td>{LABELS[r.key] ?? r.key}</td>
                    {r.values.map((v, i) => {
                      const d = r.delta[i]
                      const lower = data.better_when_lower.includes(r.key)
                      const neutral = data.neutral.includes(r.key)
                      const good = i === 0 || neutral || d.value === 0 ? null : (d.value < 0) === lower
                      return (
                        <td key={i} className={r.best === i ? 'best' : ''}>
                          {r.best === i && <Trophy size={13} className="trophy" />} {fmt(r.key, v)}
                          {i > 0 && d.value !== 0 && (
                            <span className={`dlt ${good == null ? '' : good ? 'delta-down' : 'delta-up'}`}>
                              {d.pct != null && Math.abs(d.a) >= 1 && Math.abs(d.pct) < 1000 ? `${d.pct > 0 ? '+' : ''}${num(d.pct, 1)} %` : `${d.value > 0 ? '+' : ''}${fmt(r.key, d.value)}`}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="muted" style={{ marginTop: 8 }}><Trophy size={12} /> meilleur cas sur la ligne · écarts en vert : mieux que la référence, en rouge : moins bien.</div>
          </div>
          <div className="card">
            <div className="card-head"><h2>Carte de chaque cas</h2><span className="spacer" /><span className="muted">points de regroupement et tournées</span></div>
            <div className="mini-maps">
              {data.scenarios.map((s, i) => <MiniMap key={s.scenario_id} planId={s.plan_id} title={`${i === 0 ? 'Réf. · ' : ''}${s.name}`} color={colorOf(s.scenario_id)} />)}
            </div>
          </div>
          <div className="card">
            <div className="card-head"><h2>Dépotoirs actifs (simulation)</h2></div>
            <div style={{ maxWidth: 860 }}><LineChart yLabel="dépotoirs actifs" labels={(data.scenarios[0]?.wild_dumps_daily ?? []).map((_, i) => `J${i + 1}`)}
              series={data.scenarios.map((s, i) => ({ name: `${i === 0 ? 'Réf. · ' : ''}${s.name}`, color: colorOf(s.scenario_id), values: s.wild_dumps_daily }))} /></div>
            <div className="muted">Comparer des cas de la même zone : la ville entière et la zone pilote n'ont pas la même échelle.</div>
          </div>
        </>
      )}
      {!data && !loading && <div className="card"><div className="empty">Choisir au moins deux cas (cliquer sur leurs noms), ou simuler un nouveau cas ci-dessus</div></div>}
    </div>
  )
}

const CUSTOM_PARAMS: [string, string, number][] = [
  ['walk_distance_max_m', 'Marche max jusqu\'au bac (m)', 50], ['collection_point_capacity_t', 'Capacité d\'un bac (t)', 0.5],
  ['pickup_frequency_per_week', 'Enlèvements par semaine', 1], ['work_start_h', 'Début des équipes (h)', 0.5],
  ['work_end_h', 'Fin des équipes (h)', 0.5], ['work_days_per_week', 'Jours travaillés', 1], ['fuel_price_fcfa_l', 'Gasoil (FCFA/L)', 25],
]

/** Petite carte d'un cas : ses points de regroupement et ses tournées. */
function MiniMap({ planId, title, color }: { planId: string | null; title: string; color: string }) {
  const { data: commune } = useApi(() => api.commune(), [])
  const { data: points } = useApi(() => (planId ? api.points(planId) : Promise.resolve(null)), [planId])
  const { data: routes } = useApi(() => (planId ? api.routes(planId) : Promise.resolve(null)), [planId])
  return (
    <div className="mini-map">
      <div className="mini-map-title"><span className="case-dot" style={{ background: color }} />{title}{points && <span className="muted"> · {points.features.length} points</span>}</div>
      <div className="map-wrap" style={{ height: 260 }}>
        {planId ? <MapView commune={commune} points={points} routes={routes} layers={MINI_LAYERS} fitPlan /> : <div className="empty">en calcul…</div>}
      </div>
    </div>
  )
}
const MINI_LAYERS: Layers = { quartiers: false, dumps: false, reports: false, points: true, routes: true, trucks: false }

/** Classement : quel cas gagne sur le plus d'indicateurs, en une phrase, puis l'analyse par l'IA. */
function Ranking({ data, onAnalyse, assistant }: { data: CompareMany; onAnalyse: () => void; assistant: boolean }) {
  const scored = data.rows.filter((r) => r.best != null).length
  const order = data.ranking.map((id) => data.scenarios.findIndex((s) => s.scenario_id === id))
  const top = order[0]
  const tie = order.length > 1 && data.wins[order[0]] === data.wins[order[1]]
  const text = !scored
    ? 'Tous les cas donnent les mêmes résultats.'
    : tie
      ? `Pas de vainqueur net : « ${data.scenarios[order[0]].name} » et « ${data.scenarios[order[1]].name} » gagnent chacun sur ${data.wins[order[0]]} indicateur(s) sur ${scored}.`
      : `« ${data.scenarios[top].name} » est le meilleur cas sur ${data.wins[top]} indicateur(s) sur ${scored}.`
  return (
    <div className="card verdict" role="status">
      <div className="verdict-row">
        <div style={{ flex: 1 }}>
          <b>En bref :</b> {text}
          <div className="podium">
            {order.map((i, rank) => (
              <span key={data.scenarios[i].scenario_id} className="podium-item">
                <b>{rank + 1}.</b> {data.scenarios[i].name} <span className="muted">· {data.wins[i]} victoire(s)</span>
              </span>
            ))}
          </div>
        </div>
        {assistant && (
          <button className="btn-ai" data-testid="compare-ai" onClick={onAnalyse} title="Demander à l'assistant IA d'analyser ces chiffres">
            <Sparkles size={16} /> Analyser avec l'IA
          </button>
        )}
      </div>
    </div>
  )
}
