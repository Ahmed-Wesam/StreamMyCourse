import { enterSupersededState, resetSupersededFlagForTests } from './student-session-superseded-state'

export {
  enterSupersededState,
  exitSupersededState,
  isStudentSessionSuperseded,
  syncSupersededFromStorage,
} from './student-session-superseded-state'

type SessionSupersededListener = () => void

const listeners = new Set<SessionSupersededListener>()

/** Coalesce parallel refresh-deny paths (header probe, API client, unhandledrejection). */
const NOTIFY_COOLDOWN_MS = 5000
let lastNotifyAt = 0

/** Notify student SPA listeners that the catalog API reported session_superseded. */
export function notifySessionSuperseded(): void {
  enterSupersededState()
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

/** Test helper only. */
export function resetStudentSessionSupersededForTests(): void {
  resetSupersededFlagForTests()
  listeners.clear()
}

/** Test helper only. */
export function resetSessionSupersededNotifyCooldownForTests(): void {
  lastNotifyAt = 0
}
