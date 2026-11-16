// SPDX-License-Identifier: AGPL-3.0-or-later
import { ArrowLeftRight, ClipboardList, Flag, LayoutDashboard, Map as MapIcon, SlidersHorizontal } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { api } from '../../api/client'
import type { Health } from '../../api/types'
import { useApi } from '../../state/app'

const LINKS = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/carte', label: 'Carte interactive', icon: MapIcon },
  { to: '/signalements', label: 'Signalements', icon: Flag },
  { to: '/scenario', label: 'Simulation & scénarios', icon: SlidersHorizontal },
  { to: '/comparer', label: 'Comparer', icon: ArrowLeftRight },
  { to: '/journal', label: 'Journal', icon: ClipboardList },
]

export function Logo({ size = 64 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 4C19 4 9 14 9 27c0 17 23 33 23 33s23-16 23-33C55 14 45 4 32 4z" fill="#2f9e4f" />
      <circle cx="32" cy="27" r="14" fill="#fff" />
      <path d="M24 30c2-7 11-10 18-8-1 8-8 12-16 11" fill="none" stroke="#f28c28" strokeWidth="3.4" strokeLinecap="round" />
      <path d="M24 32l9-6" stroke="#2f9e4f" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function Sidebar() {
  const { data: h } = useApi<Health>(() => api.health(), [])
  return (
    <aside className="sidebar">
      <div className="brand">
        <Logo />
        <div className="brand-title">Salu<span>bri</span></div>
        <div className="brand-sub">Assainissement de Ouaga · une ville propre</div>
      </div>
      <nav className="nav" aria-label="Navigation principale">
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'}><Icon size={20} />{label}</NavLink>
        ))}
      </nav>
      <div className="sidebar-status">
        <div className="status-row"><span className={`dot ${h?.db === 'ok' ? 'ok' : 'bad'}`} /><div><b>Serveur Salubri</b>{h ? (h.db === 'ok' ? 'En ligne, données locales' : 'Base indisponible') : 'Connexion…'}</div></div>
        <div className="status-row"><span className={`dot ${h?.osrm === 'ok' ? 'ok' : 'warn'}`} /><div><b>Itinéraires</b>{h?.osrm === 'ok' ? 'Réseau routier OSRM' : 'Distances approximatives'}</div></div>
        <div className="muted" style={{ color: '#8fa3c2' }}>Logiciel libre AGPL-3.0 · v{h?.version ?? '—'}</div>
      </div>
    </aside>
  )
}
