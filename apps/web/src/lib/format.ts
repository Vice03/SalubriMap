// SPDX-License-Identifier: AGPL-3.0-or-later
const nf = (d: number) => new Intl.NumberFormat('fr-FR', { maximumFractionDigits: d, minimumFractionDigits: 0 })

export const num = (v: number | null | undefined, d = 0) => (v == null || Number.isNaN(v) ? '—' : nf(d).format(v))
export const fcfa = (v: number | null | undefined) => (v == null ? '—' : `${nf(0).format(v)} FCFA`)
export const tonnes = (v: number | null | undefined, d = 1) => (v == null ? '—' : `${nf(d).format(v)} t`)
export const km = (v: number | null | undefined) => (v == null ? '—' : `${nf(1).format(v)} km`)
export const pct = (v: number | null | undefined, d = 0) => (v == null ? '—' : `${nf(d).format(v * 100)} %`)
export const signed = (v: number, d = 1, unit = '') => `${v > 0 ? '+' : v < 0 ? '−' : ''}${nf(d).format(Math.abs(v))}${unit}`

export function hhmm(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return `${String(h).padStart(2, '0')} h ${String(m).padStart(2, '0')}`
}

export function ago(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 0) return new Date(iso).toLocaleDateString('fr-FR')
  if (s < 60) return "à l'instant"
  if (s < 3600) return `il y a ${Math.round(s / 60)} min`
  if (s < 86400) return `il y a ${Math.round(s / 3600)} h`
  if (s < 30 * 86400) return `il y a ${Math.round(s / 86400)} j`
  return new Date(iso).toLocaleDateString('fr-FR')
}

export const date = (iso: string) =>
  new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

/** Sum a daily series into weeks (smooths twice-a-week collections). */
export function weekly(values: number[] | undefined): number[] {
  const out: number[] = []
  for (let i = 0; i < (values?.length ?? 0); i += 7) out.push((values as number[]).slice(i, i + 7).reduce((a, b) => a + b, 0))
  return out
}
