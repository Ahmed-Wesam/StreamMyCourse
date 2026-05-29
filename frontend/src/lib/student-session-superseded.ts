import { sessionSupersededUserMessage } from './session-superseded-message'

import {

  clearSessionSupersededBanner,

  persistSessionSupersededBanner,

  readSessionSupersededBanner,

} from './session-superseded-banner-storage'



type SessionSupersededListener = () => void



let supersededFlag = false

const listeners = new Set<SessionSupersededListener>()



/** Coalesce parallel refresh-deny paths (header probe, API client, unhandledrejection). */

const NOTIFY_COOLDOWN_MS = 5000

let lastNotifyAt = 0



/** Idempotent: set in-memory flag and persist banner once. */

export function enterSupersededState(): void {

  supersededFlag = true

  if (!readSessionSupersededBanner()) {

    persistSessionSupersededBanner(sessionSupersededUserMessage)

  }

}



/** Restore in-memory flag from persisted banner without fan-out to listeners. */

export function syncSupersededFromStorage(): void {

  if (readSessionSupersededBanner()) {

    supersededFlag = true

  }

}



export function isStudentSessionSuperseded(): boolean {

  return supersededFlag || readSessionSupersededBanner() !== null

}



export function exitSupersededState(): void {

  supersededFlag = false

  clearSessionSupersededBanner()

}



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

  supersededFlag = false

  listeners.clear()

}



/** Test helper only. */

export function resetSessionSupersededNotifyCooldownForTests(): void {

  lastNotifyAt = 0

}

