// SPDX-License-Identifier: AGPL-3.0-or-later
import { FileUp, Undo2 } from 'lucide-react'
import { RoleButton } from '../ui/RoleButton'
import { useState } from 'react'
import { api } from '../../api/client'
import type { ImportResult } from '../../api/types'
import { useApp } from '../../state/app'
import { Modal, StatusBadge } from '../ui/Overlay'

export function ImportDialog({ onClose }: { onClose: () => void }) {
  const { toast, refresh } = useApp()
  const [file, setFile] = useState<File | null>(null)
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState<ImportResult | null>(null)
  const [done, setDone] = useState<ImportResult | null>(null)

  const run = async (f: File, dry: boolean) => {
    setBusy(true)
    try {
      const r = await api.importFile(f, dry)
      setRes(r)
      if (!dry) { setDone(r); refresh(); toast('ok', `Import terminé : ${r.accepted} ligne(s) lues, ${r.rejected} illisible(s)`) }
    } catch (e) {
      toast('error', (e as Error).message)
    } finally { setBusy(false) }
  }
  const pick = (f: File | undefined) => { if (f) { setFile(f); setDone(null); void run(f, true) } }
  const traps = res?.report.filter((r) => r.report_status === 'rejected' || r.report_status === 'to_review').length ?? 0

  return (
    <Modal title="Importer un fichier (jeu du jury)" onClose={onClose}>
      <label className={`dropzone ${over ? 'over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]) }}>
        <FileUp size={34} color="#f28c28" />
        <div style={{ fontWeight: 700, color: '#0f172a', marginTop: 8 }}>{file ? file.name : 'Glisser-déposer un fichier ici'}</div>
        <div>GeoJSON, CSV ou ZIP (fichier + photos) — ou cliquer pour choisir</div>
        <input type="file" accept=".geojson,.json,.csv,.zip" hidden onChange={(e) => pick(e.target.files?.[0])} />
      </label>
      {res && (
        <>
          <div className="chips">
            <span className="badge" style={{ background: '#e0e7ff', color: '#1e3a8a' }}>{res.dry_run ? 'Aperçu (rien enregistré)' : 'Importé'}</span>
            <span className="badge" style={{ background: '#dcfce7', color: '#166534' }}>{res.accepted} ligne(s) lue(s)</span>
            <span className="badge" style={{ background: '#fee2e2', color: '#991b1b' }}>{res.rejected} illisible(s)</span>
            <span className="badge" style={{ background: '#ffedd5', color: '#9a3412' }}>{traps} piège(s) détecté(s)</span>
          </div>
          <div style={{ overflow: 'auto', maxHeight: '42vh' }}>
            <table className="table">
              <thead><tr><th>Ligne</th><th>Lecture</th><th>Verdict des règles</th><th>Score</th><th>Détail</th></tr></thead>
              <tbody>
                {res.report.map((r) => (
                  <tr key={r.row}>
                    <td>{r.row}{r.external_id ? <div className="muted">{r.external_id}</div> : null}</td>
                    <td>{r.status === 'accepted' ? <span className="badge" style={{ background: '#dcfce7', color: '#166534' }}>Lue</span> : <span className="badge" style={{ background: '#fee2e2', color: '#991b1b' }}>Illisible</span>}</td>
                    <td>{r.report_status ? <StatusBadge status={r.report_status} /> : '—'}</td>
                    <td>{r.score ?? '—'}</td>
                    <td style={{ fontSize: 12.5 }}>
                      {r.errors.map((e) => <div key={e} style={{ color: '#b91c1c' }}>{e}</div>)}
                      {r.warnings.map((w) => <div key={w} style={{ color: '#b45309' }}>{w}</div>)}
                      {r.rule_hits.map((h) => <div key={h.rule + h.detail}><span className="rule">{h.rule} {h.delta}</span>{h.detail}</div>)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            {done?.batch_id && (
              <RoleButton need="admin" className="btn ghost" disabled={busy} onClick={async () => {
                const r = await api.rollback(done.batch_id as string)
                toast('info', `Import annulé : ${r.reverted} signalement(s) supprimé(s)`); refresh(); onClose()
              }}><Undo2 size={16} />Annuler l'import</RoleButton>
            )}
            {res.dry_run && file && <RoleButton need="admin" className="btn primary" disabled={busy} onClick={() => void run(file, false)}>Importer pour de vrai</RoleButton>}
          </div>
        </>
      )}
      {busy && <div className="muted">Traitement en cours…</div>}
    </Modal>
  )
}
