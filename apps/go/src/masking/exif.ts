// SPDX-License-Identifier: AGPL-3.0-or-later
import exifr from 'exifr'

/** Valeurs EXIF utiles aux règles anti-pièges, lues AVANT le masquage (la photo masquée n'a plus d'EXIF). */
export interface ExifFields { lat: number | null; lon: number | null; takenAt: string | null }

/** « 2026:11:17 08:00:00 » (EXIF, heure locale sans fuseau) → « 2026-11-17T08:00:00 », comme le serveur le lisait. */
export function exifDate(raw: unknown): string | null {
  const m = typeof raw === 'string' ? /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(raw) : null
  return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}` : null
}

export async function readExif(file: Blob): Promise<ExifFields> {
  let lat: number | null = null, lon: number | null = null, takenAt: string | null = null
  try {
    const g = await exifr.gps(file)
    if (g && Number.isFinite(g.latitude) && Number.isFinite(g.longitude)) { lat = g.latitude; lon = g.longitude }
  } catch { /* pas de GPS */ }
  try {
    const d = (await exifr.parse(file, { pick: ['DateTimeOriginal'], reviveValues: false })) as { DateTimeOriginal?: string } | undefined
    takenAt = exifDate(d?.DateTimeOriginal)
  } catch { /* pas de date */ }
  return { lat, lon, takenAt }
}
