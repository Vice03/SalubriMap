// SPDX-License-Identifier: AGPL-3.0-or-later
import { WASTE } from './labels'
import { num } from './format'

export interface LaabalSite {
  id: string; lat: number; lon: number; volume_m3: number; type: string; n_signalements: number; caniveau: boolean
  nettoye_le: string | null; revu_le: string; transmis_le: string | null; auto: boolean
}
export interface LaabalZone { quartier: string; arrondissement: number | null; sites: LaabalSite[]; recidivistes: number; niveau: 'alerte' | 'critique'; caniveaux: number }
export interface LaabalAlerts { numero: string; numero_demo: boolean; auto: boolean; zones: LaabalZone[] }

const osm = (s: { lat: number; lon: number }) => `https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lon}#map=18/${s.lat}/${s.lon}`

/** Message à la brigade Laabal : zone, dépotoirs revenus après nettoyage, liens de carte. */
export function laabalMessage(z: { quartier: string; sites: Omit<LaabalSite, 'id'>[] }): string {
  const lines = z.sites.slice(0, 8).map((s) =>
    `- ${WASTE[s.type as keyof typeof WASTE] ?? s.type}, ${num(s.volume_m3, 1)} m³${s.caniveau ? ', DANS UN CANIVEAU' : ''} : ${osm(s)}`)
  return [
    'Brigade Laabal — alerte Salubri (mairie de Ouagadougou)',
    `Zone récidiviste : ${z.quartier} — ${z.sites.length} dépotoir(s) revenu(s) après nettoyage.`,
    ...lines,
    'Merci de programmer un contrôle et une sensibilisation des riverains.',
  ].join('\n')
}

/** Lien WhatsApp (wa.me) : ouvre la discussion avec le message prêt ; rien ne part sans clic de l'agent. */
export function whatsappLink(numero: string, message: string): string {
  return `https://wa.me/${numero.replace(/\D/g, '')}?text=${encodeURIComponent(message)}`
}
