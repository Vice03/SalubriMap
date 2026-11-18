// SPDX-License-Identifier: AGPL-3.0-or-later
import { Copy, MessageCircle, ShieldAlert, Waves } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client'
import { can, useSession } from '../../api/session'
import { ago, num } from '../../lib/format'
import { laabalMessage, whatsappLink, type LaabalSite } from '../../lib/laabal'
import { useApi, useApp } from '../../state/app'

type ZoneLike = { quartier: string; sites: Omit<LaabalSite, 'id'>[] }

/** Bouton « Prévenir Laabal sur WhatsApp » + copie du message (sans réseau, on le colle où l'on veut). */
export function WhatsAppLaabal({ zone, numero, demo }: { zone: ZoneLike; numero?: string; demo?: boolean }) {
  const session = useSession()
  const { toast } = useApp()
  const { data } = useApi(() => (numero || !session ? Promise.resolve(null) : api.laabalAlerts()), [numero, session?.token])
  if (!session || !can('moderateur', session)) return null
  const n = numero ?? data?.numero
  const isDemo = demo ?? data?.numero_demo
  const msg = laabalMessage(zone)
  return (
    <div className="wa-row">
      {n && (
        <a className="btn-wa" href={whatsappLink(n, msg)} target="_blank" rel="noopener noreferrer"
          title={isDemo ? 'Numéro fictif : à remplacer par celui de la brigade (SALUBRI_LAABAL_WHATSAPP dans .env)' : `WhatsApp ${n}`}>
          <MessageCircle size={16} /> Prévenir Laabal sur WhatsApp
        </a>
      )}
      <button className="pill-btn" onClick={() => { void navigator.clipboard?.writeText(msg).then(() => toast('ok', 'Message copié')).catch(() => toast('error', 'Copie impossible')) }}>
        <Copy size={14} /> Copier le message
      </button>
    </div>
  )
}

/** Tableau de bord : zones où des dépotoirs reviennent après nettoyage, transmises à la brigade Laabal. */
export function LaabalPanel() {
  const session = useSession()
  const { refreshKey } = useApp()
  const [open, setOpen] = useState<string | null>(null)
  const allowed = !!session && can('moderateur', session)
  const { data } = useApi(() => (allowed ? api.laabalAlerts() : Promise.resolve(null)), [allowed, refreshKey])
  if (!allowed || !data) return null
  return (
    <div className="card">
      <div className="card-head">
        <span className="head-icon" style={{ background: 'linear-gradient(135deg,#ff8a65,#d84315)' }}><ShieldAlert size={18} color="#fff" /></span>
        <h2>Brigade Laabal : zones récidivistes</h2><span className="spacer" />
        <span className="badge" style={{ background: data.zones.length ? '#ffe4dc' : '#e7f6ec', color: data.zones.length ? '#b23c17' : '#1b7a3a' }}>
          {data.zones.length ? `${data.zones.length} zone(s) en alerte` : 'Aucune récidive'}
        </span>
      </div>
      <p className="muted" style={{ marginTop: -6 }}>
        Un dépotoir qui revient après nettoyage est transmis {data.auto ? 'automatiquement' : 'à la main'} à la brigade (contrôle,
        sensibilisation, sanction des riverains ; elle ne ramasse pas).
        {data.numero_demo && <> Numéro WhatsApp <b>fictif</b> ({data.numero}) : à remplacer dans <code>.env</code> (<code>SALUBRI_LAABAL_WHATSAPP</code>).</>}
      </p>
      {data.zones.map((z) => (
        <div key={z.quartier} className="laabal-zone">
          <button className="laabal-head" onClick={() => setOpen(open === z.quartier ? null : z.quartier)} aria-expanded={open === z.quartier}>
            <b>{z.quartier}</b>
            <span className="muted">{z.recidivistes} récidive(s){z.caniveaux ? ` · ${z.caniveaux} dans un caniveau` : ''}</span>
            <span className="spacer" />
            <span className="badge" style={z.niveau === 'critique' ? { background: '#fee2e2', color: '#b91c1c' } : { background: '#ffedd5', color: '#c2410c' }}>
              {z.niveau === 'critique' ? 'Critique' : 'Alerte'}
            </span>
          </button>
          {open === z.quartier && (
            <ul className="laabal-sites">
              {z.sites.map((s) => (
                <li key={s.id}>
                  {s.caniveau && <Waves size={14} color="#c62828" />} {num(s.volume_m3, 1)} m³ · revu {ago(s.revu_le)}
                  {s.transmis_le && <span className="muted"> · transmis {s.auto ? 'automatiquement ' : ''}{ago(s.transmis_le)}</span>}
                </li>
              ))}
            </ul>
          )}
          <WhatsAppLaabal zone={z} numero={data.numero} demo={data.numero_demo} />
        </div>
      ))}
      {!data.zones.length && <div className="empty">Aucun dépotoir revenu après nettoyage. Essai : marquer un dépotoir « nettoyé », puis deux nouveaux signalements au même endroit.</div>}
    </div>
  )
}
