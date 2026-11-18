// SPDX-License-Identifier: AGPL-3.0-or-later
/** Camion benne vu de profil (dessin original). `body` : couleur de la benne. */
export const TRUCK_COLORS = ['#eef2f7', '#f57c00', '#2e9e44', '#1e88e5', '#00897b', '#8e24aa', '#fbc02d', '#5d4037']

export function TruckArt({ body, width = 72 }: { body: string; width?: number }) {
  const light = body === '#eef2f7' || body === '#fbc02d'
  return (
    <svg viewBox="0 0 72 44" width={width} height={(width * 44) / 72} aria-hidden="true">
      <ellipse cx="36" cy="40.5" rx="32" ry="2.5" fill="#0b2a52" opacity=".12" />
      {/* benne */}
      <path d="M4 9h40a2 2 0 0 1 2 2v20H4a2 2 0 0 1-2-2V11a2 2 0 0 1 2-2z" fill={body} stroke={light ? '#9fb0c6' : 'rgba(0,0,0,.18)'} strokeWidth="1" />
      <path d="M8 13v14M14 13v14M20 13v14M26 13v14M32 13v14M38 13v14" stroke={light ? '#c9d4e3' : 'rgba(255,255,255,.28)'} strokeWidth="1.4" />
      {/* cabine */}
      <path d="M47 15h11.5c1 0 1.9.5 2.4 1.3l5.6 8.4c.3.5.5 1 .5 1.6V31a2 2 0 0 1-2 2H47z" fill={light ? '#dbe4ef' : body} stroke="rgba(0,0,0,.18)" strokeWidth="1" />
      <path d="M50 18h8.4l4.6 7H50z" fill="#bfe3ff" stroke="#0b2a52" strokeOpacity=".25" />
      <rect x="2" y="31" width="66" height="3.5" rx="1.5" fill="#37474f" />
      <rect x="64" y="27" width="4" height="2.5" rx="1" fill="#ffd54f" />
      {/* roues */}
      {[13, 27, 57].map((x) => (
        <g key={x}><circle cx={x} cy="35.5" r="5" fill="#263238" /><circle cx={x} cy="35.5" r="2.1" fill="#b0bec5" /></g>
      ))}
    </svg>
  )
}
