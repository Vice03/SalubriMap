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

/** Logo : épingle aux couleurs du drapeau du Burkina Faso (rouge, vert) et feuille jaune (ville propre). */
export function Logo({ size = 64 }: { size?: number }) {
  const pin = 'M32 3C18.7 3 8.5 13.2 8.5 26.4 8.5 43.6 32 61 32 61s23.5-17.4 23.5-34.6C55.5 13.2 45.3 3 32 3z'
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs><clipPath id="logo-pin"><path d={pin} /></clipPath></defs>
      <g clipPath="url(#logo-pin)"><rect width="64" height="27" fill="#EF2B2D" /><rect y="27" width="64" height="40" fill="#009E49" /></g>
      <path d={pin} fill="none" stroke="#fff" strokeOpacity=".9" strokeWidth="2" />
      <circle cx="32" cy="26.5" r="13.5" fill="#fff" />
      <g transform="translate(4.5 4.8) scale(0.55)">
        <path d="M32 50c4-17 20-25 36-23-2 17-17 27-34 25" fill="#FCD116" stroke="#E0A800" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M35 53 L60 33" stroke="#009E49" strokeWidth="3" strokeLinecap="round" />
      </g>
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

/** Bas de la barre latérale : le Monument des Héros Nationaux de Ouagadougou au soleil couchant (dessin original,
 *  simplifié) et un ruban aux couleurs du Burkina Faso. */
function CityArt() {
  return (
    <svg viewBox="0 0 248 170" preserveAspectRatio="xMidYMax slice">
      <defs>
      <linearGradient id="ca-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#083a77" stopOpacity="0"/><stop offset=".5" stopColor="#5b8fd6" stopOpacity=".55"/><stop offset="1" stopColor="#ffd38a"/></linearGradient>
      <linearGradient id="ca-cream" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#e9d3a8"/><stop offset=".5" stopColor="#fbeed3"/><stop offset="1" stopColor="#dcc196"/></linearGradient>
      <linearGradient id="ca-ring" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f2b25a"/><stop offset="1" stopColor="#c9822e"/></linearGradient>
      </defs>
      <rect width="248" height="170" fill="url(#ca-sky)"/>
      <g fill="#2e7d32" opacity=".9"><circle cx="22" cy="138" r="13"/><circle cx="40" cy="142" r="10"/><circle cx="208" cy="136" r="14"/><circle cx="228" cy="141" r="10"/></g>
      <g transform="translate(30 6)">
      <path d="M70 158 C92 150 104 128 108 100 L140 100 C144 128 156 150 178 158 Z" fill="url(#ca-cream)"/>
      <path d="M118 158 C116 140 118 120 124 108 C130 120 132 140 130 158 Z" fill="#c98a3a" opacity=".85"/>
      <ellipse cx="124" cy="101" rx="30" ry="5" fill="#a86a22"/>
      <rect x="94" y="91" width="60" height="10" fill="url(#ca-ring)"/>
      <ellipse cx="124" cy="91" rx="30" ry="5" fill="#f4c27a"/>
      <g fill="#5a4a3a" opacity=".55"><rect x="101" y="94" width="5" height="4"/><rect x="109" y="94" width="5" height="4"/><rect x="117" y="94" width="5" height="4"/><rect x="125" y="94" width="5" height="4"/><rect x="133" y="94" width="5" height="4"/><rect x="141" y="94" width="5" height="4"/></g>
      <path d="M110 88 C108 70 104 52 96 40 L108 46 L114 40 L124 46 L134 40 L140 46 L152 40 C144 52 140 70 138 88 Z" fill="url(#ca-cream)"/>
      <path d="M113 86 C112 70 110 56 106 46 L110 47 C113 58 115 72 116 86 Z" fill="#2f8f3e"/>
      <path d="M135 86 C136 70 138 56 142 46 L138 47 C135 58 133 72 132 86 Z" fill="#2f8f3e"/>
      <rect x="122" y="50" width="4" height="36" fill="#b07a3a" opacity=".7"/>
      <path d="M112 46 C112 38 136 38 136 46 Z" fill="#e2a24f"/>
      <path d="M116 39 C116 32 132 32 132 39 Z" fill="#2f8f3e"/>
      <rect x="123.3" y="25" width="1.4" height="8" fill="#9aa4ad"/>
      <g fill="#9ea3a8" stroke="#7d8287" strokeWidth=".6">
      <rect x="108" y="96" width="9" height="62"/><rect x="119" y="100" width="9" height="58"/>
      <rect x="105.5" y="85" width="14" height="12" rx="3"/><rect x="116.5" y="89" width="14" height="12" rx="3"/>
      </g>
      <g stroke="#6f7479" strokeWidth=".7"><path d="M109 85v4M112.5 85v4M116 85v4M120 89v4M123.5 89v4M127 89v4"/><path d="M105.5 92h5M116.5 96h5"/></g>
      <rect x="119" y="122" width="9" height="2.2" fill="#d9b44a"/>
      <path d="M118 128 l1.6 4.6 h4.8 l-3.9 2.9 1.5 4.6 -4 -2.9 -4 2.9 1.5 -4.6 -3.9 -2.9 h4.8z" fill="#f2c12e"/>
      <rect x="60" y="152" width="128" height="6" fill="#1e5fa8" opacity=".9"/>
      <path d="M104 158 c4-8 8-8 12 0 c4-8 8-8 12 0 c4-8 8-8 12 0 Z" fill="#1e5fa8"/>
      </g>
      <path d="M248 120 L248 170 L150 170 Z" fill="#ef2b2d"/>
      <path d="M248 144 L248 170 L196 170 Z" fill="#009e49"/>
      <path d="M228 146 l2.6 7.6 h8 l-6.5 4.7 2.5 7.6 -6.6 -4.7 -6.5 4.7 2.5 -7.6 -6.5 -4.7 h8z" fill="#fcd116"/>
    </svg>
  )
}
