// SPDX-License-Identifier: AGPL-3.0-or-later
import type { WasteType } from '../../api/types'

const PATHS: Record<WasteType, string> = {
  household: 'M8 7h8l1 13H7z M10 7c0-2 4-2 4 0 M9 11h6',
  plastic: 'M10 3h4v3l2 3v11a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9l2-3z M8 13h8',
  rubble: 'M3 19h18 M5 19v-4h6v4 M11 19v-6h7v6 M7 15v-3h5v1',
  organic: 'M5 19c0-8 6-13 14-14-1 8-6 14-14 14z M5 19l8-8',
  medical: 'M15 3l6 6 M18 6L8 16l-3 1 1-3L16 4 M3 21l3-3 M4 4l16 16',
  mixed: 'M3 20h18l-4-9-3 3-3-6-4 7z',
  other: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7 M12 17h.01',
}
const BG: Record<WasteType, string> = {
  household: '#fde7d6', plastic: '#dbeafe', rubble: '#e7e2d8', organic: '#dcfce7', medical: '#fee2e2', mixed: '#f3e8ff', other: '#eef0f3',
}
const FG: Record<WasteType, string> = {
  household: '#b7410e', plastic: '#2563eb', rubble: '#6b5a45', organic: '#16a34a', medical: '#dc2626', mixed: '#9333ea', other: '#64748b',
}

export function WasteIcon({ type, size = 36 }: { type: WasteType; size?: number }) {
  return (
    <span className="waste-icon" style={{ width: size, height: size, background: BG[type] }} aria-hidden="true">
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="none" stroke={FG[type]} strokeWidth={1.9}
        strokeLinecap="round" strokeLinejoin="round">
        {PATHS[type].split(' M').map((d, i) => <path key={i} d={i ? `M${d}` : d} />)}
      </svg>
    </span>
  )
}
