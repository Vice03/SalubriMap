// SPDX-License-Identifier: AGPL-3.0-or-later
// Couleurs de la carte, séparées de MapView : le tableau de bord les utilise sans charger MapLibre (lot E).
/** Une couleur = une seule signification sur toute la carte (voir MAP_KEY). */
export const MAP_KEY = {
  plan: '#1e3a8a',      // plan de collecte : tournées, camions, points de regroupement
  problem: '#dc2626',   // problème : dépotoirs, points non desservis
  reference: '#7c3aed', // référence officielle SDGD 2020
  zone: '#475569',      // découpage (quartiers)
  verified: '#0f766e', probable: '#64748b', review: '#b45309', rejected: '#94a3b8', // signalements
}
