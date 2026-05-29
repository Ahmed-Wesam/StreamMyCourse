import { isSessionSupersededError } from './api/client'
import { readSessionSupersededBanner } from './session-superseded-banner'

/** True when the global supersede banner already covers this failure. */
export function shouldSuppressInlineSessionSupersededMessage(err?: unknown): boolean {
  if (readSessionSupersededBanner()) return true
  if (err !== undefined && isSessionSupersededError(err)) return true
  return false
}
