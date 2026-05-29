import { isCognitoRefreshSessionSupersededError } from './cognito-session-superseded'
import { notifySessionSuperseded } from './handleSessionSuperseded'

let installed = false

/**
 * Map unhandled Amplify refresh denials to the same supersede flow (avoids a stuck tab).
 * Idempotent — safe to call from student entry.
 */
export function installSessionSupersededRejectionHandler(): void {
  if (installed || typeof window === 'undefined') return
  installed = true

  window.addEventListener('unhandledrejection', (event) => {
    if (!isCognitoRefreshSessionSupersededError(event.reason)) return
    event.preventDefault()
    notifySessionSuperseded()
  })
}

/** Test helper only. */
export function resetSessionSupersededRejectionHandlerForTests(): void {
  installed = false
}
