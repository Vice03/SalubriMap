// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ButtonHTMLAttributes } from 'react'
import { denyReason, useSession, type Role } from '../../api/session'

/** Bouton d'une action réservée : désactivé, avec la raison en info-bulle, si le rôle ne suffit pas (lot A7). */
export function RoleButton({ need, disabled, title, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { need: Role }) {
  const session = useSession()
  const why = denyReason(need, session)
  return (
    <span title={why ?? title} className="role-btn">
      <button {...rest} disabled={disabled || !!why} aria-disabled={disabled || !!why} title={why ?? title} />
    </span>
  )
}
