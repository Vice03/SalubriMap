// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Position } from '../api/types'

function inRing(p: Position, ring: Position[]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/** Point in Polygon / MultiPolygon (outer rings only: enough for districts). */
export function inPolygon(p: Position, geom: { type: string; coordinates: unknown }): boolean {
  if (geom.type === 'Polygon') return inRing(p, (geom.coordinates as Position[][])[0])
  if (geom.type === 'MultiPolygon') return (geom.coordinates as Position[][][]).some((poly) => inRing(p, poly[0]))
  return false
}
