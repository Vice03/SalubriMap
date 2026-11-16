// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from 'react'

export interface Gps { lat: number; lon: number; accuracy: number | null; manual: boolean }
export type GpsState = { status: 'waiting' } | { status: 'ok'; fix: Gps } | { status: 'error'; message: string }

/** Position en continu (haute précision). Hors HTTPS, le téléphone refuse la géolocalisation. */
export function useGps(active = true): GpsState {
  const [s, setS] = useState<GpsState>({ status: 'waiting' })
  useEffect(() => {
    if (!active) return
    if (!('geolocation' in navigator)) { setS({ status: 'error', message: 'GPS non disponible sur cet appareil' }); return }
    if (!window.isSecureContext) { setS({ status: 'error', message: 'Le GPS demande une connexion sécurisée (HTTPS)' }); return }
    const id = navigator.geolocation.watchPosition(
      (p) => setS({ status: 'ok', fix: { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, manual: false } }),
      (e) => setS({ status: 'error', message: e.code === 1 ? 'Autorisez la localisation pour Salubri Go' : 'Position introuvable : sortez à découvert' }),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    )
    return () => navigator.geolocation.clearWatch(id)
  }, [active])
  return s
}

export function accuracyLevel(acc: number | null): { label: string; color: string; bg: string } {
  if (acc == null) return { label: 'Position saisie', color: '#475569', bg: '#e2e8f0' }
  if (acc <= 20) return { label: `Précis · ± ${Math.round(acc)} m`, color: '#166534', bg: '#dcfce7' }
  if (acc <= 60) return { label: `Moyen · ± ${Math.round(acc)} m`, color: '#92400e', bg: '#fef3c7' }
  return { label: `Imprécis · ± ${Math.round(acc)} m`, color: '#991b1b', bg: '#fee2e2' }
}
