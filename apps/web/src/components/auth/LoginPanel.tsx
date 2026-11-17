// SPDX-License-Identifier: AGPL-3.0-or-later
import { KeyRound, LogIn } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../../api/client'
import { setLoginOpener } from '../../api/session'
import { Modal } from '../ui/Overlay'

/** Panneau de connexion (lot A7) : ouvert par le bouton « Se connecter » ou par une action refusée (401). */
export function LoginHost() {
  const [open, setOpen] = useState<{ why?: string; done: (ok: boolean) => void } | null>(null)
  useEffect(() => {
    setLoginOpener((why) => new Promise<boolean>((done) => setOpen({ why, done })))
    return () => setLoginOpener(null)
  }, [])
  if (!open) return null
  const close = (ok: boolean) => { open.done(ok); setOpen(null) }
  return <LoginPanel why={open.why} onDone={close} />
}

function LoginPanel({ why, onDone }: { why?: string; onDone: (ok: boolean) => void }) {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const first = useRef<HTMLInputElement>(null)
  useEffect(() => { first.current?.focus() }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await api.login(login.trim(), password)
      onDone(true)
    } catch (err) {
      setError((err as Error).message)
      setPassword('')
    } finally { setBusy(false) }
  }

  return (
    <Modal title={<span style={{ display: 'flex', alignItems: 'center', gap: 10 }}><KeyRound color="#f28c28" />Connexion mairie</span>} onClose={() => onDone(false)} narrow>
      <form className="login-form" onSubmit={(e) => void submit(e)}>
        <p className="muted">{why ?? 'Modération, imports et scénarios sont réservés aux comptes de la mairie.'}</p>
        <label>Identifiant
          <input ref={first} className="input" autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} required />
        </label>
        <label>Mot de passe
          <input className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="login-error" role="alert">{error}</div>}
        <button className="btn primary big" type="submit" disabled={busy || !login || !password}>
          <LogIn size={18} />{busy ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
    </Modal>
  )
}
