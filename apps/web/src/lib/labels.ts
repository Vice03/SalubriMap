// SPDX-License-Identifier: AGPL-3.0-or-later
import type { DumpStatus, ReportStatus, VolumeClass, WasteType } from '../api/types'

export const WASTE: Record<WasteType, string> = {
  household: 'Ménager', plastic: 'Plastique', rubble: 'Gravats', organic: 'Organique',
  medical: 'Biomédical', mixed: 'Mixte', other: 'Autre',
}
export const VOLUME: Record<VolumeClass, string> = {
  bag: 'Sac', wheelbarrow: 'Brouette', cart: 'Charrette', truck: 'Camion', more: 'Plus',
}
export const STATUS: Record<ReportStatus, string> = {
  pending: 'En attente', probable: 'Probable', verified: 'Vérifié', to_review: 'À revoir', rejected: 'Rejeté', cleaned: 'Nettoyé',
}
export const STATUS_COLOR: Record<ReportStatus, string> = {
  // mêmes teintes que la carte (MAP_KEY) : le rouge reste réservé aux problèmes (dépotoirs)
  pending: '#94a3b8', probable: '#64748b', verified: '#0f766e', to_review: '#b45309', rejected: '#94a3b8', cleaned: '#0f766e',
}
export const DUMP_STATUS: Record<DumpStatus, string> = { active: 'Actif', recurring: 'Récidive', cleaned: 'Nettoyé' }
export const EVENT: Record<string, string> = {
  reports_changed: 'Nouveaux signalements', fleet_changed: 'Flotte modifiée', season_changed: 'Changement de saison',
  zone_changed: 'Nouveau quartier', budget_changed: 'Budget modifié', frequency_changed: 'Fréquences modifiées',
  subscription_changed: 'Abonnements modifiés', manual: 'Recalcul complet',
}
export const STAGES: { code: string; name: string }[] = [
  { code: 'E1', name: 'Consolidation' }, { code: 'E2', name: 'Demande' }, { code: 'E3', name: 'Points' },
  { code: 'E4', name: 'Distances' }, { code: 'E5', name: 'Tournées' }, { code: 'E6', name: 'Simulation' },
  { code: 'E7', name: 'Différences' },
]
export const AUDIT_ACTION: Record<string, string> = {
  moderate: 'Modération', merge: 'Fusion', import: 'Import', rollback: 'Import annulé', cleaned: 'Dépotoir nettoyé',
  osm_id: 'Versé dans OSM', create: 'Création', update: 'Modification', breakdown: 'Camion en panne',
  repair: 'Camion réparé', delete: 'Suppression',
}
export const TRUCK_COLORS = ['#2563eb', '#16a34a', '#f28c28', '#9333ea', '#dc2626', '#0891b2', '#ca8a04', '#db2777']
