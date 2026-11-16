// SPDX-License-Identifier: AGPL-3.0-or-later
import { ArrowDownRight, ArrowLeftRight, ArrowUpRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { LineChart } from '../components/ui/Charts'
import { num } from '../lib/format'
import { useApi, useApp } from '../state/app'

const LABELS: Record<string, string> = {
  points: 'Points de regroupement', routes: 'Tournées', km_day: 'km par jour de collecte', cost_day_fcfa: 'Coût d\'une journée (FCFA)',
  unserved_points: 'Points non desservis', demand_t_week: 'Déchets à collecter (t/semaine)',
  'sim.collected_t': 'Tonnage collecté (t)', 'sim.wild_dump_t': 'Parti en dépôt sauvage (t)',
  'sim.wild_dumps_active_final': 'Dépotoirs actifs à la fin', 'sim.wild_dumps_active_mean': 'Dépotoirs actifs (moyenne)',
  'sim.overflow_point_days': 'Débordements (points × jours)', 'sim.cost_total_fcfa': 'Coût total (FCFA)',
  'sim.cost_per_t': 'Coût par tonne (FCFA)', 'sim.coverage_rate': 'Couverture', 'sim.subscription_rate_final': 'Taux d\'abonnement final',
  'sim.mean_cleanup_delay_days': 'Délai moyen de nettoyage (j)',
}
const PRESETS: { name: string; params?: Record<string, unknown>; breakdown?: number }[] = [
  { name: '2 camions en panne', breakdown: 2 },
  { name: 'Saison des pluies', params: { season: 'rain' } },
  { name: 'Abonnement +20 pts', params: { subscription_rate_delta: 0.2 } },
  { name: 'Budget −30 %', params: { budget_factor: 0.7 } },
]

export function ComparePage() {
  const { scenarios, scenario, reloadScenarios, track, toast } = useApp()
  const [a, setA] = useState<string>('')
  const [b, setB] = useState<string>('')
  useEffect(() => {
    if (!a && scenario) setA(scenario.id)
    if (!b && scenarios.length > 1) setB(scenarios.find((s) => s.id !== (a || scenario?.id))?.id ?? '')
  }, [scenarios, scenario, a, b])
  const { data, loading } = useApi(() => (a && b ? api.compare(a, b) : Promise.resolve(null)), [a, b])

  const preset = async (p: typeof PRESETS[number]) => {
    const base = scenarios.find((s) => s.id === a)
    if (!base) return
    try {
      const params: Record<string, unknown> = {}
      if (p.params?.season) params.season = p.params.season
      if (p.params?.subscription_rate_delta) params.subscription_rate = Math.min(1, Number(base.params.subscription_rate) + 0.2)
      if (p.params?.budget_factor) params.budget_fcfa_month = Number(base.params.budget_fcfa_month) * 0.7
      const sc = await api.createScenario(`${base.name} — ${p.name}`, base.id, params)
      let planId = sc.plan_version_id
      if (p.breakdown) {
        const vs = sc.vehicles.filter((v) => !v.out_of_service).slice(-p.breakdown)
        const r = await api.patchScenario(sc.id, { vehicles: vs.map((v) => ({ id: v.id, out_of_service: true })) })
        if (r.plan_version_id) planId = r.plan_version_id
      }
      await reloadScenarios()
      setB(sc.id)
      track(planId, p.name)
    } catch (e) { toast('error', (e as Error).message) }
  }

  return (
    <div className="content">
      <div className="card">
        <div className="card-head"><ArrowLeftRight color="#0f2b55" /><h2>Comparer deux scénarios</h2></div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <select className="select" value={a} onChange={(e) => setA(e.target.value)} aria-label="Scénario A">
            {scenarios.map((s) => <option key={s.id} value={s.id}>A — {s.name}</option>)}
          </select>
          <select className="select" value={b} onChange={(e) => setB(e.target.value)} aria-label="Scénario B">
            <option value="">B — choisir…</option>
            {scenarios.map((s) => <option key={s.id} value={s.id}>B — {s.name}</option>)}
          </select>
          <span className="muted">ou créer B à partir de A :</span>
          {PRESETS.map((p) => <button key={p.name} className="pill-btn" onClick={() => void preset(p)}>{p.name}</button>)}
        </div>
      </div>
      {data && (
        <div className="grid row-map">
          <div className="card" style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead><tr><th>Indicateur</th><th>A · {data.a.name}</th><th>B · {data.b.name}</th><th>Écart</th></tr></thead>
              <tbody>
                {Object.entries(data.delta).map(([k, d]) => {
                  const lower = data.better_when_lower.includes(k)
                  const neutral = ['points', 'routes', 'demand_t_week'].includes(k)
                  const better = d.value === 0 || neutral ? null : (d.value < 0) === lower
                  const isRate = k.endsWith('rate') || k.endsWith('rate_final')
                  const f = (x: number) => (isRate ? `${num(x * 100, 1)} %` : num(x, Math.abs(x) < 10 ? 1 : 0))
                  return (
                    <tr key={k}>
                      <td>{LABELS[k] ?? k}</td><td>{f(d.a)}</td><td>{f(d.b)}</td>
                      <td className={better == null ? '' : better ? 'delta-down' : 'delta-up'}>
                        {better != null && (d.value > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />)}
                        {' '}{d.pct != null && Math.abs(d.a) >= 1 && Math.abs(d.pct) < 1000 ? `${d.pct > 0 ? '+' : ''}${num(d.pct, 1)} %` : `${d.value > 0 ? '+' : ''}${f(d.value)}`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="card">
            <div className="card-head"><h2>Dépotoirs actifs (simulation)</h2></div>
            <LineChart yLabel="dépotoirs actifs" labels={data.a.wild_dumps_daily.map((_, i) => `J${i + 1}`)} series={[
              { name: `A · ${data.a.name}`, color: '#2563eb', values: data.a.wild_dumps_daily },
              { name: `B · ${data.b.name}`, color: '#dc2626', values: data.b.wild_dumps_daily },
            ]} />
            <div className="muted">Vert : le scénario B fait mieux · rouge : il fait moins bien.</div>
          </div>
        </div>
      )}
      {!data && !loading && <div className="card"><div className="empty">Choisir deux scénarios</div></div>}
    </div>
  )
}
