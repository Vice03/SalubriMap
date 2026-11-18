// SPDX-License-Identifier: AGPL-3.0-or-later
import { ArrowLeftRight, ClipboardList, Flag, LayoutDashboard, Map as MapIcon, SlidersHorizontal } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { api } from '../../api/client'
import type { Health, Stats } from '../../api/types'
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
  const { data: st } = useApi<Stats>(() => api.stats(), [])
  const toReview = (st?.by_status.to_review ?? 0) + (st?.by_status.pending ?? 0)
  return (
    <aside className="sidebar">
      <div className="brand">
        <Logo />
        <div className="brand-title">Salu<span>bri</span></div>
        <div className="brand-sub">Assainissement de Ouaga · une ville propre</div>
      </div>
      <nav className="nav" aria-label="Navigation principale">
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'}><Icon size={20} />{label}
            {to === '/signalements' && toReview > 0 && <span className="nav-count" title={`${toReview} signalement(s) à vérifier`}>{toReview > 99 ? '99+' : toReview}</span>}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-status">
        <div className="status-row"><span className={`dot ${h?.db === 'ok' ? 'ok' : 'bad'}`} /><div><b>Serveur Salubri</b>{h ? (h.db === 'ok' ? 'En ligne, données locales' : 'Base indisponible') : 'Connexion…'}</div></div>
        <div className="status-row"><span className={`dot ${h?.osrm === 'ok' ? 'ok' : 'warn'}`} /><div><b>Itinéraires</b>{h?.osrm === 'ok' ? 'Réseau routier OSRM' : 'Distances approximatives'}</div></div>
        <div className="muted" style={{ color: '#b9d3f3' }}>Logiciel libre AGPL-3.0 · v{h?.version ?? '—'}</div>
      </div>
      <div className="sidebar-art" aria-hidden="true">
        <CityArt />
        <div className="city"><b>Ouagadougou</b><span>Capitale du Burkina Faso</span></div>
      </div>
    </aside>
  )
}

/** Bas de la barre latérale : silhouette de ville au soleil couchant et ruban aux couleurs du Burkina Faso (dessin original). */
function CityArt() {
  return (
    <svg viewBox="0 0 248 150" preserveAspectRatio="xMidYMax slice">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#083a77" stopOpacity="0" /><stop offset=".55" stopColor="#f6a54a" stopOpacity=".55" /><stop offset="1" stopColor="#ffcf73" /></linearGradient>
      </defs>
      <rect width="248" height="150" fill="url(#sky)" />
      <circle cx="176" cy="92" r="20" fill="#ffd36b" opacity=".9" />
      {/* immeubles */}
      <g fill="#7b4a2a" opacity=".85">
        <rect x="8" y="88" width="16" height="50" /><rect x="26" y="76" width="12" height="62" /><rect x="40" y="94" width="18" height="44" />
        <rect x="150" y="84" width="14" height="54" /><rect x="166" y="98" width="20" height="40" /><rect x="188" y="80" width="12" height="58" /><rect x="202" y="92" width="22" height="46" />
      </g>
      {/* monument : colonne et anneau */}
      <g fill="#a0522d">
        <path d="M100 138 L104 70 L112 70 L116 138 Z" />
        <ellipse cx="108" cy="66" rx="16" ry="6" fill="none" stroke="#a0522d" strokeWidth="4" />
        <rect x="88" y="128" width="40" height="10" rx="2" />
      </g>
      {/* arbres */}
      <g fill="#2e7d32"><circle cx="70" cy="122" r="11" /><circle cx="82" cy="126" r="8" /><circle cx="138" cy="124" r="9" /><circle cx="232" cy="122" r="10" /></g>
      {/* ruban : rouge, vert, étoile jaune */}
      <path d="M248 106 L248 150 L150 150 Z" fill="#ef2b2d" />
      <path d="M248 128 L248 150 L196 150 Z" fill="#009e49" />
      <path d="M226 128 l2.6 7.6 h8 l-6.5 4.7 2.5 7.6 -6.6 -4.7 -6.5 4.7 2.5 -7.6 -6.5 -4.7 h8z" fill="#fcd116" />
    </svg>
  )
}
