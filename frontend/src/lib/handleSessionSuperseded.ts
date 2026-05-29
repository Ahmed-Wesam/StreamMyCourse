import { suspendStudentSessionRefreshMetadata } from './student-session-refresh'
import {
  armSessionSupersedeHandling,
  clearSessionSupersedeHandling,
} from './session-supersede-handling'

type SessionSupersededListener = () => void

const listeners = new Set<SessionSupersededListener>()

/** Coalesce parallel refresh-deny paths (header probe, API client, unhandledrejection). */
const NOTIFY_COOLDOWN_MS = 5000
let lastNotifyAt = 0

/** Arm latch, suspend refresh metadata, and wipe stale Amplify caches (reload + notify). */
export function reapplySessionSupersedeGuards(): void {
  armSessionSupersedeHandling()
  suspendStudentSessionRefreshMetadata()
  void import('./clear-amplify-auth-caches').then(({ clearAmplifyAuthCaches }) => {
    clearAmplifyAuthCaches()
  })
}

/** Notify student SPA listeners that the catalog API reported session_superseded. */
export function notifySessionSuperseded(): void {
  reapplySessionSupersedeGuards()
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
  clearSessionSupersedeHandling()
}

/** Reset notify cooldown only — test helper when listeners must stay subscribed. */
export function resetSessionSupersededNotifyCooldownForTests(): void {
  lastNotifyAt = 0
}
