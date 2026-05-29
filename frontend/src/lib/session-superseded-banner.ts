import { clearAmplifyAuthCaches } from './clear-amplify-auth-caches'
import { clearSessionSupersedeHandling } from './session-supersede-handling'
import { restoreStudentSessionRefreshMetadata } from './student-session-refresh'

/** sessionStorage key — survives route change to /login so the supersede message stays visible. */
export const SESSION_SUPERSEDED_BANNER_KEY = 'smc:sessionSupersededMessage'

type SessionSupersededDismissListener = () => void

const dismissListeners = new Set<SessionSupersededDismissListener>()

export function persistSessionSupersededBanner(message: string): void {
  try {
    sessionStorage.setItem(SESSION_SUPERSEDED_BANNER_KEY, message)
  } catch {
    /* ignore */
  }
}

export function readSessionSupersededBanner(): string | null {
  try {
    const raw = sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)
    return raw?.trim() ? raw.trim() : null
  } catch {
    return null
  }
}

export function clearSessionSupersededBanner(): void {
  try {
    sessionStorage.removeItem(SESSION_SUPERSEDED_BANNER_KEY)
  } catch {
    /* ignore */
  }
}

/** Subscribe to user dismiss of the global supersede banner (e.g. revoke lesson playback). */
export function subscribeSessionSupersededDismiss(listener: SessionSupersededDismissListener): () => void {
  dismissListeners.add(listener)
  return () => {
    dismissListeners.delete(listener)
  }
}

/** User dismissed the banner: hide UI, release latch, and wipe stale Amplify caches. */
export function dismissSessionSupersededBannerUi(): void {
  clearSessionSupersededBanner()
  clearSessionSupersedeHandling()
  restoreStudentSessionRefreshMetadata()
  clearAmplifyAuthCaches()
  for (const listener of dismissListeners) {
    listener()
  }
}

/** Test helper only. */
export function resetSessionSupersededDismissListenersForTests(): void {
  dismissListeners.clear()
}
