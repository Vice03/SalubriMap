// SPDX-License-Identifier: AGPL-3.0-or-later
/** Petit bus : n'importe quelle page peut ouvrir l'assistant avec une question déjà écrite.
 *  Sans le module (éteint), personne n'écoute : la page affiche alors son propre message. */
export const ASK_EVENT = 'salubri:assistant-ask'

export function askAssistant(question: string): void {
  window.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: question }))
}
