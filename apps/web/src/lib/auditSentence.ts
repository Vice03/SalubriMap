// SPDX-License-Identifier: AGPL-3.0-or-later
/** Lot E : une ligne du journal en phrase française (« Saison passée à « pluies » »), pas en clés techniques. */
import type { AuditEntry } from '../api/types'

const SEASON: Record<string, string> = { dry: 'sèche', rain: 'pluies' }
const STATUS: Record<string, string> = {
  verified: 'vérifié', rejected: 'rejeté', to_review: 'à revoir', probable: 'probable', cleaned: 'nettoyé', pending: 'en attente',
}
const PARAM: Record<string, string> = {
  budget_fcfa_month: 'Budget mensuel', subscription_rate: "Taux d'abonnement", season: 'Saison',
  pickups_per_truck_week: 'Enlèvements par camion', laabal_ops_week: 'Opérations Laabal',
}

const val = (k: string, v: unknown): string => {
  if (k === 'season' && typeof v === 'string') return `« ${SEASON[v] ?? v} »`
  if (k === 'status' && typeof v === 'string') return `« ${STATUS[v] ?? v} »`
  if (k.endsWith('rate') && typeof v === 'number') return `${Math.round(v * 100)} %`
  if (typeof v === 'number') return v.toLocaleString('fr-FR')
  return typeof v === 'object' ? JSON.stringify(v) : String(v)
}

export function auditSentence(a: AuditEntry): string {
  const after = a.after ?? {}
  switch (a.action) {
    case 'moderate': return `Signalement ${STATUS[String(after.status)] ?? String(after.status ?? '')}${after.note ? ` (« ${String(after.note)} »)` : ''}`
    case 'import': return `Import de ${after.accepted ?? '?'} signalement(s)${after.filename ? ` depuis « ${String(after.filename)} »` : ''}`
    case 'rollback': return `Import annulé : ${after.reverted ?? '?'} signalement(s) retiré(s)`
    case 'breakdown': return `Camion ${String(after.label ?? '')} déclaré en panne`.replace('  ', ' ')
    case 'repair': return `Camion ${String(after.label ?? '')} remis en service`.replace('  ', ' ')
    case 'cleaned': return 'Dépotoir marqué nettoyé'
    case 'laabal_alert': return after.auto ? `Dépotoir revenu après nettoyage : transmis automatiquement à la brigade Laabal${after.caniveau ? ' (dans un caniveau)' : ''}` : 'Dépotoir transmis à la brigade Laabal'
    case 'merge': return 'Signalements fusionnés (doublon)'
    case 'login': return 'Connexion'
    case 'login_failed': return `Échec de connexion${after.login ? ` pour « ${String(after.login)} »` : ''}`
    case 'logout': return 'Déconnexion'
  }
  const params = (after.params ?? after) as Record<string, unknown>
  const parts = Object.entries(params)
    .filter(([k]) => PARAM[k] || k === 'season' || k === 'status')
    .map(([k, v]) => (k === 'season' ? `Saison passée à ${val(k, v)}` : `${PARAM[k] ?? k} : ${val(k, v)}`))
  if (parts.length) return parts.join(' · ')
  return a.action === 'create' ? 'Création' : a.action === 'delete' ? 'Suppression' : 'Modification'
}
