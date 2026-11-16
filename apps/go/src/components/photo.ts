// SPDX-License-Identifier: AGPL-3.0-or-later
/** Garde la photo d'origine (l'EXIF sert aux règles anti-pièges) ; ne réduit que si elle dépasse 12 Mo. */
export async function preparePhoto(file: File): Promise<Blob> {
  if (file.size <= 12 * 1024 * 1024) return file
  const bmp = await createImageBitmap(file)
  const scale = Math.min(1, 1280 / Math.max(bmp.width, bmp.height))
  const c = document.createElement('canvas')
  c.width = Math.round(bmp.width * scale)
  c.height = Math.round(bmp.height * scale)
  c.getContext('2d')!.drawImage(bmp, 0, 0, c.width, c.height)
  return new Promise((res) => c.toBlob((b) => res(b ?? file), 'image/jpeg', 0.85))
}
