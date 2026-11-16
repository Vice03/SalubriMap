// SPDX-License-Identifier: AGPL-3.0-or-later
import { useState } from 'react'
import { num } from '../../lib/format'

export function Sparkline({ values, color, width = 130, height = 44 }: { values: number[]; color: string; width?: number; height?: number }) {
  if (values.length < 2) return null
  const max = Math.max(...values, 1e-9)
  const min = Math.min(...values, 0)
  const pts = values.map((v, i) => [(i / (values.length - 1)) * width, height - 4 - ((v - min) / (max - min || 1)) * (height - 10)])
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  const id = `g${color.replace('#', '')}`
  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" width="100%" height={30} aria-hidden="true">
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity="0.35" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient></defs>
      <path d={`${line} L${width},${height} L0,${height} Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth={2.2} />
    </svg>
  )
}

/** Graduations « rondes » (1, 2, 2,5 ou 5 × 10^n) couvrant [0, max]. */
export function niceTicks(max: number, count = 4): number[] {
  if (!(max > 0)) return [0, 1]
  const raw = max / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) ?? 10) * mag
  const top = Math.ceil(max / step) * step
  return Array.from({ length: Math.round(top / step) + 1 }, (_, i) => +(i * step).toFixed(6))
}

export interface Series { name: string; color: string; values: number[]; unit?: string }

export function LineChart({ series, labels, height = 220, yLabel }: { series: Series[]; labels: string[]; height?: number; yLabel?: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 640
  const pad = { l: 52, r: 14, t: yLabel ? 22 : 12, b: 26 }
  const n = Math.max(...series.map((s) => s.values.length), 0)
  if (n < 2) return <div className="empty">Pas encore de données</div>
  const ticks = niceTicks(Math.max(...series.flatMap((s) => s.values), 1e-9))
  const max = ticks[ticks.length - 1]
  const x = (i: number) => pad.l + (i / (n - 1)) * (W - pad.l - pad.r)
  const y = (v: number) => pad.t + (1 - v / max) * (height - pad.t - pad.b)
  const step = Math.ceil(n / 8)
  return (
    <div style={{ position: 'relative' }}>
      <div className="chips" style={{ marginBottom: 6 }}>
        {series.map((s) => <span key={s.name} className="muted" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><span className="swatch" style={{ background: s.color, borderRadius: 99 }} />{s.name}</span>)}
      </div>
      <svg viewBox={`0 0 ${W} ${height}`} width="100%" role="img" aria-label={series.map((s) => s.name).join(', ')}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
          const px = ((e.clientX - r.left) / r.width) * W
          setHover(Math.max(0, Math.min(n - 1, Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (n - 1)))))
        }}>
        {yLabel && <text x={4} y={11} fontSize="11" fill="#64748b">{yLabel}</text>}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? '#cbd5e1' : '#eef2f7'} />
            <text x={pad.l - 8} y={y(t) + 4} fontSize="11" textAnchor="end" fill="#64748b">{num(t, Number.isInteger(t) ? 0 : 1)}</text>
          </g>
        ))}
        {labels.map((l, i) => (i % step === 0 ? <text key={i} x={x(i)} y={height - 6} fontSize="11" textAnchor="middle" fill="#94a3b8">{l}</text> : null))}
        {series.map((s) => {
          const d = s.values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
          return (
            <g key={s.name}>
              {series.length === 1 && <path d={`${d} L${x(s.values.length - 1)},${y(0)} L${x(0)},${y(0)} Z`} fill={s.color} opacity={0.08} />}
              <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            </g>
          )
        })}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={height - pad.b} stroke="#cbd5e1" strokeDasharray="3 3" />}
        {hover != null && series.map((s) => <circle key={s.name} cx={x(hover)} cy={y(s.values[hover] ?? 0)} r={4} fill={s.color} stroke="#fff" strokeWidth={2} />)}
      </svg>
      {hover != null && (
        <div style={{ position: 'absolute', top: 30, left: `${(x(hover) / W) * 100}%`, transform: 'translateX(-50%)', background: '#0b1f3d', color: '#fff', borderRadius: 8, padding: '6px 10px', fontSize: 12, pointerEvents: 'none', whiteSpace: 'nowrap' }}>
          <b>{labels[hover]}</b>
          {series.map((s) => <div key={s.name}>{s.name} : {num(s.values[hover] ?? 0, 1)}{s.unit ?? ''}</div>)}
        </div>
      )}
    </div>
  )
}
