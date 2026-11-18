// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, Construction, Inbox, Languages, MapPin, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { outbox } from './db'
import { PwaBars } from './components/PwaBars'
import { NearbyPage } from './pages/NearbyPage'
import { OutboxPage } from './pages/OutboxPage'
import { ReportPage } from './pages/ReportPage'
import { onOutboxChange, startAutoSync } from './sync'
import { RoadReportPage } from './modules/seasons/RoadReportPage'
import { useSeasonsEnabled } from './modules/seasons/useSeasons'
import { ServerSetup } from './components/ServerSetup'
import { getServer, isNative } from './server'
import { LangPicker } from './voice/LangPicker'
import { getLang, setLang, type LangChoice } from './voice/script'
import { VoiceFlow } from './voice/VoiceFlow'

type Tab = 'report' | 'outbox' | 'nearby' | 'road'

/** Application Android : sans adresse de serveur enregistrée, on la demande d'abord. */
export function App() {
  const [, bump] = useState(0)
  const [editing, setEditing] = useState(false)
  if (isNative() && (!getServer() || editing)) return <ServerSetup onSaved={() => { setEditing(false); bump((n) => n + 1) }} onCancel={getServer() ? () => setEditing(false) : undefined} />
  return <Main onChangeServer={isNative() ? () => setEditing(true) : undefined} />
}

function Main({ onChangeServer }: { onChangeServer?: () => void }) {
  const [tab, setTab] = useState<Tab>('report')
  const [online, setOnline] = useState(navigator.onLine)
  const [pending, setPending] = useState(0)
  const [key, setKey] = useState(0)
  const [lang, setLangState] = useState<LangChoice | null>(getLang()) // guide vocal : langue choisie au lancement
  const [classic, setClassic] = useState(false) // formulaire classique pour ce signalement seulement
  const seasons = useSeasonsEnabled() // module « Saisons » : onglet « Route » seulement s'il est allumé
  useEffect(() => {
    const up = () => setOnline(navigator.onLine)
    window.addEventListener('online', up); window.addEventListener('offline', up)
    const stop = startAutoSync()
    const count = () => void outbox.all().then((a) => setPending(a.filter((i) => i.state === 'pending').length))
    count()
    const off = onOutboxChange(count)
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', up); stop(); off() }
  }, [])
  if (lang === null) return <LangPicker onPick={(l) => { setLang(l); setLangState(l) }} />
  return (
    <div className="app">
      <header>
        <div className="brand"><img src={`${import.meta.env.BASE_URL}icon.svg`} alt="" /><div><b>Salubri <span>Go</span></b><small>Signalez un dépotoir, la mairie planifie</small></div></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="icon" aria-label="Changer de langue" onClick={() => { setLang(null); setLangState(null) }}><Languages size={20} /></button>
          <span className={`net ${online ? 'on' : 'off'}`}>{online ? <Wifi size={14} /> : <WifiOff size={14} />}{online ? 'En ligne' : 'Hors ligne'}</span>
        </div>
      </header>
      <main>
        {tab === 'report' && (lang !== 'off' && !classic
          ? <VoiceFlow key={key} lang={lang} onSent={() => { setTab('outbox'); setKey(key + 1) }} onAgain={() => setKey(key + 1)} onClassic={() => setClassic(true)} />
          : <ReportPage key={key} onSent={() => { setTab('outbox'); setKey(key + 1); setClassic(false) }} />)}
        {tab === 'outbox' && <OutboxPage />}
        {tab === 'nearby' && <NearbyPage />}
        {seasons && tab === 'road' && <RoadReportPage />}
      </main>
      <PwaBars />
      {onChangeServer && <p style={{ textAlign: 'center', margin: '0 0 96px', fontSize: 13 }}><a href="#" onClick={(e) => { e.preventDefault(); onChangeServer() }}>Changer de serveur</a></p>}
      <nav aria-label="Navigation principale">
        <button className={tab === 'report' ? 'on' : ''} onClick={() => setTab('report')}><Camera size={22} />Signaler</button>
        <button className={tab === 'outbox' ? 'on' : ''} onClick={() => setTab('outbox')}><Inbox size={22} />Mes envois{pending > 0 && <i>{pending}</i>}</button>
        <button className={tab === 'nearby' ? 'on' : ''} onClick={() => setTab('nearby')}><MapPin size={22} />Autour de moi</button>
        {seasons && <button className={tab === 'road' ? 'on' : ''} onClick={() => setTab('road')}><Construction size={22} />Route</button>}
      </nav>
    </div>
  )
}
