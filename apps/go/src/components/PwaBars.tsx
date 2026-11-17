// SPDX-License-Identifier: AGPL-3.0-or-later
import { Download, RefreshCw, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface InstallEvent extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }

/** Lot D : « Installer l'application » (Android/Chrome) et avis de nouvelle version (service worker en attente). */
export function PwaBars() {
  const [install, setInstall] = useState<InstallEvent | null>(null)
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null)
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const onPrompt = (e: Event) => { e.preventDefault(); setInstall(e as InstallEvent) }
    window.addEventListener('beforeinstallprompt', onPrompt)
    const onUpdate = (e: Event) => setWaiting((e as CustomEvent<ServiceWorker>).detail)
    window.addEventListener('salubri-sw-update', onUpdate)
    return () => { window.removeEventListener('beforeinstallprompt', onPrompt); window.removeEventListener('salubri-sw-update', onUpdate) }
  }, [])

  if (waiting) {
    return (
      <div className="update-bar" role="status">
        <RefreshCw size={18} />Une nouvelle version de Salubri Go est prête.
        <button className="btn primary small" onClick={() => { waiting.postMessage('skipWaiting'); window.location.reload() }}>Mettre à jour</button>
      </div>
    )
  }
  if (install && !hidden) {
    return (
      <div className="install-bar" role="dialog" aria-label="Installer l'application">
        <Download size={18} />Installer Salubri Go sur ce téléphone : il s'ouvre même sans réseau.
        <button className="btn primary small" onClick={async () => { await install.prompt(); setInstall(null) }}>Installer l'application</button>
        <button className="icon" aria-label="Plus tard" onClick={() => setHidden(true)}><X size={16} /></button>
      </div>
    )
  }
  return null
}
