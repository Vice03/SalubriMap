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

/** Logo : épingle aux couleurs du drapeau du Burkina Faso (rouge, vert, étoile jaune). */
export function Logo({ size = 64 }: { size?: number }) {
  const pin = 'M32 3C18.7 3 8.5 13.2 8.5 26.4 8.5 43.6 32 61 32 61s23.5-17.4 23.5-34.6C55.5 13.2 45.3 3 32 3z'
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs><clipPath id="logo-pin"><path d={pin} /></clipPath></defs>
      <g clipPath="url(#logo-pin)"><rect width="64" height="27" fill="#EF2B2D" /><rect y="27" width="64" height="40" fill="#009E49" /></g>
      <path d={pin} fill="none" stroke="#fff" strokeOpacity=".9" strokeWidth="2" />
      <circle cx="32" cy="26.5" r="13.5" fill="#fff" />
      <path d="M32.00,17.70 L34.29,24.14 L41.13,24.33 L35.71,28.51 L37.64,35.07 L32.00,31.20 L26.36,35.07 L28.29,28.51 L22.87,24.33 L29.71,24.14Z" fill="#FCD116" stroke="#E0A800" strokeWidth="1" strokeLinejoin="round" />
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
