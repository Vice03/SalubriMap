// SPDX-License-Identifier: AGPL-3.0-or-later
import type { VolumeClass, WasteType } from './db'

export const WASTE: { k: WasteType; label: string; emoji: string; color: string }[] = [
  { k: 'household', label: 'Ordures ménagères', emoji: '🗑️', color: '#0f766e' },
  { k: 'plastic', label: 'Plastiques', emoji: '🧴', color: '#2563eb' },
  { k: 'organic', label: 'Organiques', emoji: '🥬', color: '#65a30d' },
  { k: 'rubble', label: 'Gravats', emoji: '🧱', color: '#92400e' },
  { k: 'medical', label: 'Biomédical', emoji: '💉', color: '#dc2626' },
  { k: 'mixed', label: 'Mélangé', emoji: '♻️', color: '#7c3aed' },
]
export const VOLUME: { k: VolumeClass; label: string; hint: string }[] = [
  { k: 'bag', label: 'Sac', hint: '< 0,1 m³' },
  { k: 'wheelbarrow', label: 'Brouette', hint: '≈ 0,1 m³' },
  { k: 'cart', label: 'Charrette', hint: '≈ 0,5 m³' },
  { k: 'truck', label: 'Camion', hint: '≈ 5 m³' },
  { k: 'more', label: 'Plus', hint: '> 5 m³' },
]
export const STATUS: Record<string, { label: string; color: string }> = {
  verified: { label: 'Vérifié', color: '#0f766e' },
  probable: { label: 'Probable', color: '#475569' },
  to_review: { label: 'À revoir par la mairie', color: '#b45309' },
  rejected: { label: 'Rejeté', color: '#64748b' },
  pending: { label: 'En attente', color: '#64748b' },
  cleaned: { label: 'Nettoyé', color: '#0f766e' },
}
