type SessionSupersededListener = () => void

const listeners = new Set<SessionSupersededListener>()

/** Coalesce parallel refresh-deny paths (header probe, API client, unhandledrejection). */
const NOTIFY_COOLDOWN_MS = 5000
let lastNotifyAt = 0

/** Notify student SPA listeners that the catalog API reported session_superseded. */
export function notifySessionSuperseded(): void {
  const now = Date.now()
  if (now - lastNotifyAt < NOTIFY_COOLDOWN_MS) return
  lastNotifyAt = now
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
  lastNotifyAt = 0
}

/** Reset notify cooldown only — test helper when listeners must stay subscribed. */
export function resetSessionSupersededNotifyCooldownForTests(): void {
  lastNotifyAt = 0
}
