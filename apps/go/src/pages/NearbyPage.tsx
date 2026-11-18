// SPDX-License-Identifier: AGPL-3.0-or-later
import { Navigation } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useGps } from '../components/useGps'
import { apiUrl } from '../server'

interface Dump {
  geometry: { coordinates: [number, number] }
  properties: { id: string; status: string; n_reports: number; volume_est_m3: number; site_kind?: string; ref?: string | null }
}
const KIND: Record<string, string> = { sauvage: 'Dépôt sauvage', encadree: 'Décharge encadrée (DSPH)', autre: 'Autre site de dépôt' }
const OUAGA = { lat: 12.3714, lon: -1.5197 }

function dist(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180
  const x = (b.lon - a.lon) * r * Math.cos(((a.lat + b.lat) / 2) * r)
  return Math.hypot(x, (b.lat - a.lat) * r) * 6_371_000
}

export function NearbyPage() {
  const gps = useGps()
  const here = gps.status === 'ok' ? gps.fix : OUAGA
  const [dumps, setDumps] = useState<Dump[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const key = `${here.lat.toFixed(3)},${here.lon.toFixed(3)}`
  useEffect(() => {
    const d = 0.02 // ≈ 2 km
    const q = new URLSearchParams({ bbox: [here.lon - d, here.lat - d, here.lon + d, here.lat + d].join(',') })
    q.append('status', 'active'); q.append('status', 'recurring')
    fetch(apiUrl(`/api/dump-sites?${q}`)).then((r) => r.json()).then((fc) => { setDumps(fc.features); setErr(null) })
      .catch(() => setErr('Hors ligne : la liste se charge au retour du réseau'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  const list = (dumps ?? []).map((f) => ({ f, m: dist(here, { lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }) })).sort((a, b) => a.m - b.m).slice(0, 30)
  return (
    <div className="page">
      <p className="hint">{gps.status === 'ok' ? 'Dépotoirs connus à moins de 2 km de vous.' : 'GPS indisponible : dépotoirs autour du centre-ville.'}</p>
      {err && <p className="hint center">{err}</p>}
      {dumps && !list.length && <p className="hint center">Aucun dépotoir connu autour de vous. 👍</p>}
      {list.map(({ f, m }) => {
        const [lon, lat] = f.geometry.coordinates
        const p = f.properties
        return (
          <div key={p.id} className="card item">
            <div className="tri">⚠️</div>
            <div className="item-body">
              <b>{KIND[p.site_kind ?? 'sauvage'] ?? 'Dépôt sauvage'}</b>
              <div className="hint">{p.ref ? `Réf. ${p.ref}` : `Signalé ${p.n_reports} fois`}{p.status === 'recurring' ? ' · récidive' : ''}</div>
              <span className="pill" style={{ background: '#eef2ff', color: '#1e3a8a' }}>{m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`}</span>
            </div>
            <a className="icon" aria-label="Itinéraire" href={`https://www.openstreetmap.org/directions?to=${lat},${lon}#map=17/${lat}/${lon}`} target="_blank" rel="noreferrer"><Navigation size={18} /></a>
          </div>
        )
      })}
    </div>
  )
}
