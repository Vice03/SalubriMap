// SPDX-License-Identifier: AGPL-3.0-or-later
import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import type { ReportStatus } from '../../api/types'
import { STATUS, STATUS_COLOR } from '../../lib/labels'

function useEscape(onClose: () => void) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
}

export function Drawer({ title, onClose, children }: { title: ReactNode; onClose: () => void; children: ReactNode }) {
  useEscape(onClose)
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-head"><h2 style={{ fontSize: 18, flex: 1 }}>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Fermer"><X /></button></div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  )
}

export function Modal({ title, onClose, children }: { title: ReactNode; onClose: () => void; children: ReactNode }) {
  useEscape(onClose)
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal="true">
        <div className="drawer-head"><h2 style={{ fontSize: 18, flex: 1 }}>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Fermer"><X /></button></div>
        <div className="drawer-body">{children}</div>
      </div>
    </>
  )
}

export function StatusBadge({ status }: { status: ReportStatus }) {
  const c = STATUS_COLOR[status]
  return <span className="badge" style={{ background: `${c}1a`, color: c }}><span className="alert-dot" style={{ background: c }} />{STATUS[status]}</span>
}
