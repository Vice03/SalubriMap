// SPDX-License-Identifier: AGPL-3.0-or-later
import { Component, type ReactNode } from 'react'

/** Lot E : une erreur dans une page n'éteint plus toute l'application ; les autres pages restent utilisables. */
export class PageBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="page-error" role="alert">
        <b>Cette page a rencontré un problème.</b> Les autres pages restent utilisables.
        <div className="muted" style={{ margin: '6px 0 10px' }}>{this.state.error.message}</div>
        <button className="btn ghost" onClick={() => this.setState({ error: null })}>Réessayer</button>
      </div>
    )
  }
}
