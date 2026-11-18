// SPDX-License-Identifier: AGPL-3.0-or-later
import { existsSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { AUDIO_IDS, LANG_CUES, audioUrl } from '../voice/script'

describe('guide vocal', () => {
  it('chaque phrase du parcours a son fichier français', () => {
    const manquants = [...AUDIO_IDS, ...LANG_CUES.filter((c) => c.lang === 'fr').map((c) => c.cue.id)].filter((id) => !existsSync(`public/audio/fr/${id}.mp3`))
    expect(manquants).toEqual([])
  })
  it('21 phrases + 2 voix de langue', () => { expect(AUDIO_IDS).toHaveLength(21); expect(LANG_CUES).toHaveLength(2) })
  it("l'adresse des fichiers suit la langue", () => { expect(audioUrl('mos', 'qty_bag')).toMatch(/audio\/mos\/qty_bag\.mp3$/) })
})

describe('voix mooré', () => {
  it('les 22 fichiers du parcours sont présents', () => {
    const attendus = [...AUDIO_IDS, ...LANG_CUES.filter((c) => c.lang === 'mos').map((c) => c.cue.id)]
    expect(attendus.filter((id) => !existsSync(`public/audio/mos/${id}.mp3`))).toEqual([])
  })
})
