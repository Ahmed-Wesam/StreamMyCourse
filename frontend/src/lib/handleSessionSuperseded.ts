type SessionSupersededListener = () => void

const listeners = new Set<SessionSupersededListener>()

/** Notify student SPA listeners that the catalog API reported session_superseded. */
export function notifySessionSuperseded(): void {
  for (const listener of listeners) {
    listener()
  }
}

/** Subscribe to session_superseded events (returns unsubscribe). */
export function subscribeSessionSuperseded(listener: SessionSupersededListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Clear listeners — test helper only. */
export function resetSessionSupersededListenersForTests(): void {
  listeners.clear()
}
