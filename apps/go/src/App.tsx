// SPDX-License-Identifier: AGPL-3.0-or-later
import { Camera, Construction, Inbox, MapPin, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { outbox } from './db'
import { PwaBars } from './components/PwaBars'
import { NearbyPage } from './pages/NearbyPage'
import { OutboxPage } from './pages/OutboxPage'
import { ReportPage } from './pages/ReportPage'
import { onOutboxChange, startAutoSync } from './sync'
import { RoadReportPage } from './modules/seasons/RoadReportPage'
import { useSeasonsEnabled } from './modules/seasons/useSeasons'

type Tab = 'report' | 'outbox' | 'nearby' | 'road'

export function App() {
  const [tab, setTab] = useState<Tab>('report')
  const [online, setOnline] = useState(navigator.onLine)
  const [pending, setPending] = useState(0)
  const [key, setKey] = useState(0)
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
  return (
    <div className="app">
      <header>
        <div className="brand"><img src="/go/icon.svg" alt="" /><div><b>Salubri <span>Go</span></b><small>Signalez un dépotoir, la mairie planifie</small></div></div>
        <span className={`net ${online ? 'on' : 'off'}`}>{online ? <Wifi size={14} /> : <WifiOff size={14} />}{online ? 'En ligne' : 'Hors ligne'}</span>
      </header>
      <main>
        {tab === 'report' && <ReportPage key={key} onSent={() => { setTab('outbox'); setKey(key + 1) }} />}
        {tab === 'outbox' && <OutboxPage />}
        {tab === 'nearby' && <NearbyPage />}
        {seasons && tab === 'road' && <RoadReportPage />}
      </main>
      <PwaBars />
      <nav aria-label="Navigation principale">
        <button className={tab === 'report' ? 'on' : ''} onClick={() => setTab('report')}><Camera size={22} />Signaler</button>
        <button className={tab === 'outbox' ? 'on' : ''} onClick={() => setTab('outbox')}><Inbox size={22} />Mes envois{pending > 0 && <i>{pending}</i>}</button>
        <button className={tab === 'nearby' ? 'on' : ''} onClick={() => setTab('nearby')}><MapPin size={22} />Autour de moi</button>
        {seasons && <button className={tab === 'road' ? 'on' : ''} onClick={() => setTab('road')}><Construction size={22} />Route</button>}
      </nav>
    </div>
  )
}
