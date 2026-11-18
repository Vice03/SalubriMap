// SPDX-License-Identifier: AGPL-3.0-or-later
import { Clock, Coins, Fuel, Users, Wrench } from 'lucide-react'
import type { Couts } from '../../api/types'
import { fcfa, num } from '../../lib/format'

export const COST_LINES: [string, string, string][] = [
  ['carburant', 'Gasoil', '#ef6c00'],
  ['entretien', 'Entretien et pneus', '#8e24aa'],
  ['equipages', 'Équipages (chauffeurs + ripeurs)', '#1565c0'],
  ['amortissement_camions', 'Camions (amortissement)', '#00838f'],
  ['assurance_camions', 'Assurance et visite', '#6d4c41'],
  ['amortissement_bacs', 'Bacs (amortissement)', '#2e7d32'],
]

/** Estimation des coûts mensuels du plan : barres par poste, total, coût par tonne, comparaison au budget. */
export function CostCard({ c }: { c: Couts | undefined }) {
  if (!c) return <div className="empty">Estimation disponible après le prochain calcul du plan.</div>
  const max = Math.max(...COST_LINES.map(([k]) => c.mois_fcfa[k] ?? 0), 1)
  return (
    <div className="cost-card">
      <div className="cost-total">
        <div><div className="muted">Par mois</div><b>{fcfa(c.total_mois_fcfa)}</b></div>
        <div><div className="muted">Par an</div><b>{fcfa(c.total_an_fcfa)}</b></div>
        <div><div className="muted">Par tonne</div><b>{fcfa(c.cout_par_tonne_fcfa)}</b></div>
      </div>
      <div className={`cost-budget ${c.dans_le_budget ? 'ok' : 'bad'}`}>
        {c.dans_le_budget ? 'Dans le budget' : 'Au-dessus du budget'} de {fcfa(c.budget_mois_fcfa)} par mois
        {!c.dans_le_budget && <> (écart {fcfa(c.total_mois_fcfa - c.budget_mois_fcfa)})</>}
      </div>
      {COST_LINES.map(([k, label, color]) => (
        <div key={k} className="cost-line">
          <span className="cost-label">{label}</span>
          <span className="cost-bar"><i style={{ width: `${(100 * (c.mois_fcfa[k] ?? 0)) / max}%`, background: color }} /></span>
          <b>{fcfa(c.mois_fcfa[k])}</b>
        </div>
      ))}
      <div className="cost-facts">
        <span><Clock size={15} />{c.horaires.debut} – {c.horaires.fin} (pause {c.horaires.pause_min} min), {c.horaires.jours_semaine} j/semaine</span>
        <span><Fuel size={15} />{num(c.km_mois)} km et {num(c.gasoil_litres_mois)} L de gasoil par mois</span>
        <span><Wrench size={15} />{fcfa(c.cout_km_fcfa)} par km (gasoil + entretien)</span>
        <span><Users size={15} />{num(c.agents)} agents pour {num(c.camions_flotte)} camion(s)</span>
        <span><Coins size={15} />{num(c.journees_collecte_semaine)} journée(s) de collecte par semaine</span>
      </div>
      <div className="muted" style={{ fontSize: 12.5 }}>Estimation : prix et salaires réglables dans « Coûts » ci-dessus (sources dans docs/PARAMETRES.md).</div>
    </div>
  )
}
