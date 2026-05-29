import { clearAmplifyAuthCaches } from './clear-amplify-auth-caches'
import { exitSupersededState } from './student-session-superseded-state'

export {
  clearSessionSupersededBanner,
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
  SESSION_SUPERSEDED_BANNER_KEY,
} from './session-superseded-banner-storage'

type SessionSupersededDismissListener = () => void

const dismissListeners = new Set<SessionSupersededDismissListener>()

/** Subscribe to user dismiss of the global supersede banner (e.g. revoke lesson playback). */
export function subscribeSessionSupersededDismiss(listener: SessionSupersededDismissListener): () => void {
  dismissListeners.add(listener)
  return () => {
    dismissListeners.delete(listener)
  }
}

/** User dismissed the banner: hide UI, release supersede state, and wipe stale Amplify caches. */
export function dismissSessionSupersededBannerUi(): void {
  exitSupersededState()
  clearAmplifyAuthCaches()
  for (const listener of dismissListeners) {
    listener()
  }
}

/** Test helper only. */
export function resetSessionSupersededDismissListenersForTests(): void {
  dismissListeners.clear()
}
