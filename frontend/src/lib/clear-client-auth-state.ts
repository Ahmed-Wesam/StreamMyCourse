import { clearAmplifyAuthCaches } from './clear-amplify-auth-caches'
import {
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
} from './session-superseded-banner'
import { exitSupersededState } from './student-session-superseded'

type ClearClientAuthStateOptions = {
  /** When false, keep the session-superseded banner in sessionStorage (default). */
  clearSupersededBanner?: boolean
}

/**
 * Best-effort wipe of browser auth artifacts (Amplify may also use IndexedDB).
 * Shared by header sign-out and session-superseded handling.
 */
export function clearClientAuthState(options: ClearClientAuthStateOptions = {}): void {
  if (options.clearSupersededBanner === true) {
    exitSupersededState()
  }
  const preserveBanner = options.clearSupersededBanner !== true
  const supersededMessage = preserveBanner ? readSessionSupersededBanner() : null
  try {
    localStorage.clear()
  } catch {
    /* ignore */
  }
  clearAmplifyAuthCaches()
  try {
    sessionStorage.clear()
  } catch {
    /* ignore */
  }
  if (supersededMessage) {
    persistSessionSupersededBanner(supersededMessage)
  }

  try {
    const cookies = document.cookie ? document.cookie.split(';') : []
    for (const raw of cookies) {
      const eqPos = raw.indexOf('=')
      const name = (eqPos > -1 ? raw.slice(0, eqPos) : raw).trim()
      if (!name) continue
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    }
  } catch {
    /* ignore */
  }
}
