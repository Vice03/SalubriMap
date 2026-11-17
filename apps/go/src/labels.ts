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
/** Quantités en images (lot D) : on montre ce que le citoyen voit, pas des m³ (gardés en info-bulle). */
export const VOLUME: { k: VolumeClass; label: string; hint: string; emoji: string }[] = [
  { k: 'bag', label: 'Un sac', hint: 'moins de 0,1 m³', emoji: '🛍️' },
  { k: 'wheelbarrow', label: 'Une brouette', hint: 'environ 0,1 m³', emoji: '🧺' },
  { k: 'cart', label: 'Une charrette', hint: 'environ 0,5 m³', emoji: '🛒' },
  { k: 'truck', label: 'Un camion', hint: 'environ 5 m³', emoji: '🚚' },
  { k: 'more', label: 'Plus encore', hint: 'plus de 5 m³', emoji: '⛰️' },
]
export const STATUS: Record<string, { label: string; color: string }> = {
  verified: { label: 'Vérifié', color: '#0f766e' },
  probable: { label: 'Probable', color: '#475569' },
  to_review: { label: 'À revoir par la mairie', color: '#b45309' },
  rejected: { label: 'Rejeté', color: '#64748b' },
  pending: { label: 'En attente', color: '#64748b' },
  cleaned: { label: 'Nettoyé', color: '#0f766e' },
}

/** Ce que voit le citoyen (lot D) : jamais « Rejeté · 0/100 », une phrase et une couleur. */
export function citizenVerdict(status: string): { text: string; color: string; bg: string } {
  if (status === 'verified' || status === 'cleaned') return { text: 'Signalement confirmé', color: '#166534', bg: '#dcfce7' }
  if (status === 'rejected') return { text: "Nous n'avons pas pu confirmer ce signalement", color: '#7c2d12', bg: '#ffedd5' }
  return { text: 'Merci ! La mairie va vérifier', color: '#1e3a8a', bg: '#e0e7ff' }
}

export const STEPS: { k: 'recu' | 'verifie' | 'planifie' | 'nettoye'; label: string }[] = [
  { k: 'recu', label: 'Reçu' },
  { k: 'verifie', label: 'Vérifié' },
  { k: 'planifie', label: 'Planifié' },
  { k: 'nettoye', label: 'Nettoyé' },
]
