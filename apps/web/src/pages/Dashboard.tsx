// SPDX-License-Identifier: AGPL-3.0-or-later
import { ArrowDown, ArrowRight, ArrowUp, Bell, ChevronDown, Layers as LayersIcon, Map as MapIcon, MapPin, Recycle, Trash2, Truck, TrendingUp } from 'lucide-react'
import { lazy, Suspense, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { DumpProps, Feature, PointGeom, WasteType } from '../api/types'
import { FleetPanel } from '../components/dashboard/FleetPanel'
import { LaabalPanel, WhatsAppLaabal } from '../components/dashboard/LaabalPanel'
import type { Layers } from '../components/map/MapView'
import { MAP_KEY, WATER_DIST_M } from '../components/map/mapKey'
// MapLibre (~800 Ko) n'est chargé qu'à l'affichage de la carte : premier écran plus léger (lot E)
const MapView = lazy(() => import('../components/map/MapView').then((m) => ({ default: m.MapView })))
import { LineChart, Sparkline } from '../components/ui/Charts'
import { Drawer } from '../components/ui/Overlay'
import { WasteIcon } from '../components/ui/WasteIcon'
import { loadAlerts } from '../lib/alerts'
import { ago, num, pct, tonnes, weekly } from '../lib/format'
import { inPolygon } from '../lib/geo'
import { DUMP_STATUS, WASTE } from '../lib/labels'
import { useApi, useApp } from '../state/app'

const LEVEL = { red: '#e53935', orange: '#f9a825', blue: '#1e88e5', green: '#2e9e44' }

const K = MAP_KEY
const Dot = ({ fill, stroke, r = 6, w = 2 }: { fill: string; stroke: string; r?: number; w?: number }) => (
  <svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r={r} fill={fill} stroke={stroke} strokeWidth={w} /></svg>)
const SYMBOL: Record<string, JSX.Element> = {
  trucks: <svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="8" fill={K.plan} /><rect x="4.5" y="6" width="6" height="5" fill="#fff" rx="1" /><path d="M10.5 7.5h2l1.5 2v1.5h-3.5z" fill="#fff" /></svg>,
  points: <Dot fill="#fff" stroke={K.plan} r={6.5} w={2.5} />,
  dumps: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M9 2 L17 16 H1 Z" fill={K.problem} /><rect x="8.2" y="7" width="1.6" height="5" fill="#fff" /></svg>,
  routes: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M2 13 L7 6 L11 11 L16 4" fill="none" stroke={K.plan} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  quartiers: <svg width="18" height="18" viewBox="0 0 18 18"><rect x="2.5" y="2.5" width="13" height="13" fill="none" stroke={K.zone} strokeWidth="1.5" strokeDasharray="3 2" /></svg>,
  reports: <Dot fill={K.verified} stroke="#fff" r={5} />,
  sdgd: <Dot fill={K.reference} stroke={K.reference} r={5} />,
  heat: <svg width="18" height="18" viewBox="0 0 18 18"><defs><radialGradient id="hg"><stop offset="0" stopColor="#d32f2f" /><stop offset=".5" stopColor="#fdd835" /><stop offset="1" stopColor="#4fc3f7" stopOpacity="0" /></radialGradient></defs><circle cx="9" cy="9" r="8.5" fill="url(#hg)" /></svg>,
  water: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M2 10c2-5 6-7 10-6s5 6 2 9-8 3-11 1z" fill="#29b6f6" fillOpacity=".55" stroke="#0277bd" strokeWidth="1.4" /></svg>,
}

export function LayerToggles({ layers, setLayers }: { layers: Layers; setLayers: (l: Layers) => void }) {
  const items: [keyof Layers, string][] = [
    ['trucks', 'Camions'], ['routes', 'Tournées (survoler pour isoler)'], ['points', 'Points de regroupement'],
    ['dumps', 'Dépotoirs'], ['reports', 'Signalements'], ['quartiers', 'Quartiers'],
    ['sdgd', 'Décharges et CCT existants (réf. SDGD 2020)'],
    ['heat', 'Carte de chaleur des signalements'], ['water', "Retenues d'eau"],
  ]
  // Légende repliable (flèche) : sur un petit écran ou une carte chargée, elle ne cache plus les points.
  // Ouverte par défaut sur grand écran ; le choix est retenu sur ce navigateur.
  const [open, setOpenState] = useState<boolean>(() => {
    try { const v = localStorage.getItem('salubri.legende'); if (v) return v === '1' } catch { /* stockage indisponible */ }
    return typeof window === 'undefined' || window.innerWidth > 900
  })
  const setOpen = (v: boolean) => { setOpenState(v); try { localStorage.setItem('salubri.legende', v ? '1' : '0') } catch { /* stockage indisponible */ } }
  const on = items.filter(([k]) => layers[k]).length
  return (
    <div className={`layer-box${open ? '' : ' closed'}`}>
      <button type="button" className="layer-head" onClick={() => setOpen(!open)} aria-expanded={open} data-testid="legend-toggle"
        title={open ? 'Replier la légende' : 'Déplier la légende'}>
        <LayersIcon size={16} /><b>Légende</b>{!open && <span className="layer-count">{on}</span>}
        <ChevronDown size={16} className="layer-chev" />
      </button>
      {open && items.map(([k, label]) => (
        <div key={k}>
          <label><input type="checkbox" checked={!!layers[k]} onChange={(e) => setLayers({ ...layers, [k]: e.target.checked })} /><span className="sym">{SYMBOL[k]}</span>{label}</label>
          {k === 'points' && layers.points && <div className="sub"><span><Dot fill="#fff" stroke={K.problem} r={5} />non desservi</span></div>}
          {k === 'reports' && layers.reports && <div className="sub">
            <span><Dot fill={K.verified} stroke="#fff" r={5} />vérifié</span><span><Dot fill={K.probable} stroke="#fff" r={5} />probable</span>
            <span><Dot fill="#fff" stroke={K.review} r={4.5} />à revoir</span><span><Dot fill="#fff" stroke={K.rejected} r={4.5} />rejeté</span></div>}
          {k === 'heat' && layers.heat && <div className="sub">
            <span><select className="select" style={{ padding: '3px 8px', fontSize: 12.5 }} value={layers.heatDays ?? 0} aria-label="Période de la carte de chaleur"
              onChange={(e) => setLayers({ ...layers, heatDays: Number(e.target.value) })}>
              <option value={7}>7 derniers jours</option><option value={30}>30 derniers jours</option><option value={90}>90 derniers jours</option><option value={0}>toute la période</option>
            </select></span>
            <span className="heat-scale"><i />peu → beaucoup</span></div>}
          {k === 'water' && layers.water && <div className="sub">
            <span><Dot fill="rgba(41,182,246,0.25)" stroke="#0277bd" r={6.5} w={2} />dépotoir à moins de {WATER_DIST_M} m</span></div>}
          {k === 'sdgd' && layers.sdgd && <div className="sub">
            <span><Dot fill={K.reference} stroke={K.reference} r={4.5} />CCT</span><span><Dot fill="#fff" stroke={K.reference} r={5} w={2.5} />décharge</span>
            <span><Dot fill="#fff" stroke={K.reference} r={7.5} w={2.5} />CTVD</span></div>}
        </div>
      ))}
    </div>
  )
}

const SITE_KIND = { sauvage: 'Dépôt sauvage', encadree: 'Décharge encadrée (DSPH)', autre: 'Autre site de dépôt' } as const

export function DumpDrawer({ f, onClose }: { f: Feature<PointGeom, DumpProps>; onClose: () => void }) {
  const { toast, refresh } = useApp()
  const d = f.properties
  return (
    <Drawer title={SITE_KIND[d.site_kind ?? 'sauvage']} onClose={onClose}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <WasteIcon type={d.waste_type} size={52} />
        <div><b style={{ fontSize: 18 }}>{SITE_KIND[d.site_kind ?? 'sauvage']}</b><div className="muted">{d.ref ? `Réf. ${d.ref}` : `Signalé ${d.n_reports} fois par les citoyens`}</div><div className="muted">{WASTE[d.waste_type]} · {DUMP_STATUS[d.status]}</div></div>
      </div>
      <table className="table"><tbody>
        <tr><td>Volume estimé</td><td><b>{num(d.volume_est_m3, 1)} m³</b></td></tr>
        <tr><td>Priorité d'intervention</td><td><b>{num(d.priority, 1)}</b></td></tr>
        <tr><td>Eau</td><td>{d.near_drain ? <b style={{ color: '#c62828' }}>Dans ou au bord d'un caniveau : risque d'inondation (priorité × 2)</b> : d.near_water ? "Près d'un cours d'eau (priorité × 1,5)" : 'Non'}</td></tr>
        <tr><td>Premier signalement</td><td>{ago(d.first_reported_at)}</td></tr>
        <tr><td>Dernier signalement</td><td>{ago(d.last_reported_at)}</td></tr>
        <tr><td>Confiance moyenne</td><td>{num(d.confidence)} / 100</td></tr>
      </tbody></table>
      {d.status !== 'cleaned' && (
        <button className="btn green" onClick={async () => {
          try { await api.cleaned(d.id); toast('ok', 'Dépotoir marqué nettoyé'); refresh(); onClose() } catch (e) { toast('error', (e as Error).message) }
        }}>Marquer nettoyé (services techniques)</button>
      )}
      {d.status !== 'cleaned' && (
        <button className="btn ghost" style={{ marginTop: 8 }} onClick={async () => {
          try { await api.toLaabal(d.id); toast('ok', 'Transmis à la brigade Laabal : contrôle et sensibilisation des riverains') } catch (e) { toast('error', (e as Error).message) }
        }}>Signaler à la brigade Laabal (contrôle civique)</button>
      )}
      {d.status !== 'cleaned' && <WhatsAppLaabal zone={{ quartier: 'Dépotoir signalé', sites: [{ lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0],
        volume_m3: d.volume_est_m3, type: d.waste_type, n_signalements: d.n_reports, caniveau: !!d.near_drain, nettoye_le: null, revu_le: d.last_reported_at, transmis_le: null, auto: false }] }} />}
    </Drawer>
  )
}

export function Dashboard() {
  const nav = useNavigate()
  const { scenario } = useApp()
  const planId = scenario?.latest_ready_plan_id ?? null
  const { data: commune } = useApi(() => api.commune(), [])
  const { data: stats } = useApi(() => api.stats(), [])
  const { data: quartiers } = useApi(() => api.quartiers(), [])
  const { data: dumps } = useApi(() => api.dumps({ status: ['active', 'recurring'] }), [])
  const { data: reports } = useApi(() => api.reports({ limit: 1000 }), [])
  const { data: plan } = useApi(() => (planId ? api.plan(planId, true) : Promise.resolve(null)), [planId])
  const { data: points } = useApi(() => (planId ? api.points(planId) : Promise.resolve(null)), [planId])
  const { data: routes } = useApi(() => (planId ? api.routes(planId) : Promise.resolve(null)), [planId])
  const { data: alerts } = useApi(() => loadAlerts(scenario), [scenario?.id, planId])
  const [layers, setLayers] = useState<Layers>({ quartiers: true, dumps: true, reports: false, points: true, routes: true, trucks: true })
  const [dump, setDump] = useState<Feature<PointGeom, DumpProps> | null>(null)
  const [weeks, setWeeks] = useState(13)

  const perDay = useMemo(() => {
    const out = new Array(14).fill(0)
    const now = Date.now()
    for (const f of reports?.features ?? []) {
      const d = Math.floor((now - new Date(f.properties.reported_at).getTime()) / 86400000)
      if (d >= 0 && d < 14) out[13 - d] += 1
    }
    return out
  }, [reports])
  const newDumps = (dumps?.features ?? []).filter((f) => Date.now() - new Date(f.properties.first_reported_at).getTime() < 7 * 86400000).length
  const v = scenario?.vehicles ?? []
  const broken = v.filter((x) => x.out_of_service).length
  const pts = points?.features ?? []
  const saturated = pts.filter((f) => (f.properties.fill_ratio_per_pickup ?? 0) > 1).length
  const unserved = pts.filter((f) => f.properties.unserved).length
  const sim = plan?.summary.sim ?? {}
  const daily = plan?.summary.sim_daily ?? {}

  const zones = useMemo(() => {
    if (!quartiers || !dumps) return []
    return quartiers.features.map((q) => {
      const inside = dumps.features.filter((d) => inPolygon(d.geometry.coordinates, q.geometry))
      const vol = inside.reduce((s, d) => s + d.properties.volume_est_m3, 0)
      const water = inside.filter((d) => d.properties.near_water).length
      const drain = inside.filter((d) => d.properties.near_drain).length
      const types: Partial<Record<WasteType, number>> = {}
      inside.forEach((d) => { types[d.properties.waste_type] = (types[d.properties.waste_type] ?? 0) + 1 })
      const top = (Object.entries(types).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'household') as WasteType
      return { q, n: inside.length, vol, water, drain, top, score: inside.reduce((s, d) => s + d.properties.priority, 0) }
    }).filter((z) => z.n > 0).sort((a, b) => b.score - a.score).slice(0, 3)
  }, [quartiers, dumps])

  const kpis = [
    { icon: <Trash2 size={28} />, bg: 'linear-gradient(135deg, #2f80ed 0%, #0a4f9c 100%)', value: num((stats?.dump_sites.active ?? 0) + (stats?.dump_sites.recurring ?? 0)), label: 'Dépotoirs actifs',
      sub: <><ArrowUp size={14} />{newDumps} nouveau{newDumps > 1 ? 'x' : ''} cette semaine</>, subColor: '#0a4f9c', spark: perDay, sc: '#1a8cf0' },
    { icon: <Truck size={28} />, bg: 'var(--grad-sky)', value: `${v.length - broken}/${v.length}`, label: 'Camions disponibles',
      sub: broken ? <><ArrowDown size={14} />{broken} en panne</> : <><ArrowUp size={14} />100 % opérationnels</>, subColor: broken ? '#dc2626' : '#16a34a',
      spark: weekly(daily.truck_km), sc: '#14b8c4' },
    { icon: <MapPin size={28} />, bg: 'var(--grad-orange)', value: num(pts.length), label: 'Points de regroupement',
      sub: unserved ? <><ArrowUp size={14} />{unserved} non desservi(s){plan?.summary.trucks_needed ? ` · ≈ ${plan.summary.trucks_needed} camions nécessaires` : ''}</> : <><ArrowUp size={14} />{saturated} saturé(s)</>, subColor: unserved || saturated ? '#dc2626' : '#16a34a',
      spark: weekly(daily.overflow_points), sc: '#f59e0b' },
    { icon: <Recycle size={28} />, bg: 'var(--grad-green)', value: tonnes(sim.collected_t, 0), label: 'Déchets collectés (90 j simulés)',
      sub: <><TrendingUp size={14} />couverture {pct(sim.coverage_rate)}</>, subColor: '#16a34a',
      spark: weekly(daily.truck_collected_t), sc: '#22c55e' },
  ]

  return (
    <div className="content">
      <div className="grid kpis">
        {kpis.map((k) => (
          <div key={k.label} className="card kpi">
            <div className="kpi-icon" style={{ background: k.bg }}>{k.icon}</div>
            <div style={{ zIndex: 1 }}>
              <div className="kpi-value">{k.value}</div>
              <div className="kpi-label">{k.label}</div>
              <div className="kpi-sub" style={{ color: k.subColor }}>{k.sub}</div>
            </div>
            <div className="spark-wrap" title="Tendance sur la simulation (par semaine)" style={{ flexBasis: '100%' }}><Sparkline values={k.spark} color={k.sc} /></div>
          </div>
        ))}
      </div>

      <div className="grid row-map">
        <div className="card">
          <div className="card-head">
            <span className="head-icon" style={{ background: 'var(--grad-blue)' }}><MapIcon size={18} color="#fff" /></span><h2>Carte de Ouagadougou</h2><span className="spacer" />
            {plan && <span className="muted">Plan v{plan.version} · {num(plan.summary.km_day, 0)} km/jour · {plan.summary.routes} tournées</span>}
            <button className="pill-btn" onClick={() => nav('/carte')}>Plein écran <ArrowRight size={14} /></button>
          </div>
          <div className="map-wrap">
            <Suspense fallback={<div className="map-skeleton" aria-label="Chargement de la carte" />}>
              <MapView commune={commune} quartiers={quartiers} dumps={dumps} reports={reports} points={points} routes={routes} layers={layers}
                onDump={(id) => setDump(dumps?.features.find((f) => f.properties.id === id) ?? null)} />
            </Suspense>
            <LayerToggles layers={layers} setLayers={setLayers} />
            {plan?.distance_mode === 'approx' && <div className="map-banner">Distances approximatives (OSRM indisponible) : les tournées sont tracées en ligne droite.</div>}
          </div>
        </div>
        <FleetPanel scenario={scenario} routes={routes} />
      </div>

      <div className="grid row-3">
        <div className="card">
          <div className="card-head">
            <span className="head-icon" style={{ background: 'var(--grad-blue)' }}><TrendingUp size={18} color="#fff" /></span><h2>Indicateurs clés</h2><span className="spacer" />
            <select className="select" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} aria-label="Période">
              <option value={4}>4 semaines</option><option value={8}>8 semaines</option><option value={13}>13 semaines</option>
            </select>
          </div>
          <LineChart yLabel="tonnes par semaine" labels={Array.from({ length: weeks }, (_, i) => `S${i + 1}`)} series={[
            { name: 'Collecté par les camions', color: '#1a8cf0', values: weekly(daily.truck_collected_t).slice(0, weeks), unit: ' t' },
            { name: 'Parti en dépôt sauvage', color: '#22a447', values: weekly(daily.wild_new_t).slice(0, weeks), unit: ' t' },
          ]} />
          <div className="muted">Simulation sur 90 jours du scénario « {scenario?.name ?? '—'} ». S1 plus basse : démarrage, les points se remplissent avant le premier enlèvement.</div>
        </div>

        <div className="card">
          <div className="card-head">
            <span className="head-icon" style={{ background: 'linear-gradient(135deg,#ff6b6b,#d62828)' }}><MapPin size={18} color="#fff" /></span><h2>Zones critiques</h2><span className="spacer" />
            <span className="badge" style={{ background: '#fef3c7', color: '#92400e' }}>{zones.length} zone(s) sensible(s)</span>
          </div>
          {zones.map((z, i) => {
            const lvl = i === 0 ? { t: 'Critique', bg: '#fee2e2', c: '#b91c1c' } : i === 1 ? { t: 'Attention', bg: '#ffedd5', c: '#c2410c' } : { t: 'Surveiller', bg: '#fef3c7', c: '#a16207' }
            return (
              <div key={z.q.properties.id} className="list-item">
                <WasteIcon type={z.top} size={54} />
                <div style={{ flex: 1 }}>
                  <b>{z.q.properties.name}</b>
                  <div style={{ color: '#dc2626', fontSize: 13 }}>{z.n} dépotoir(s) · {num(z.vol, 1)} m³{z.drain ? ` · ${z.drain} dans un caniveau` : z.water ? ` · ${z.water} près de l'eau` : ''}</div>
                </div>
                <span className="badge" style={{ background: lvl.bg, color: lvl.c }}>{lvl.t}</span>
              </div>
            )
          })}
          {!zones.length && <div className="empty">Aucun dépotoir actif</div>}
        </div>

        <div className="card">
          <div className="card-head">
            <span className="head-icon" style={{ background: 'var(--grad-orange)' }}><Bell size={18} color="#fff" /></span><h2>Alertes récentes</h2><span className="spacer" />
            <button className="link" onClick={() => nav('/journal')}>Voir tout <ArrowRight size={14} /></button>
          </div>
          {(alerts ?? []).slice(0, 5).map((a) => (
            <div key={a.id} className="list-item">
              <span className="alert-dot" style={{ background: LEVEL[a.level] }} />
              <span style={{ flex: 1, fontSize: 14 }}>{a.text}</span>
              {a.at && <span className="muted">{ago(a.at)}</span>}
            </div>
          ))}
          {!alerts?.length && <div className="empty">Aucune alerte</div>}
        </div>
      </div>
      <LaabalPanel />
      {dump && <DumpDrawer f={dump} onClose={() => setDump(null)} />}
    </div>
  )
}
