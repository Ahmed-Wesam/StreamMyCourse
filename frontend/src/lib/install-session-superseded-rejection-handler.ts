import { isCognitoRefreshSessionSupersededError } from './cognito-session-superseded'
import { notifySessionSuperseded } from './student-session-superseded'

let rejectionHandlerInstalled = false

/**
 * Map unhandled Amplify refresh denials to the same supersede flow (avoids a stuck tab).
 * Student entry only — dynamic import keeps this off the first-load entry chunk.
 */
export function installSessionSupersededRejectionHandler(): void {
  if (rejectionHandlerInstalled || typeof window === 'undefined') return
  rejectionHandlerInstalled = true

  window.addEventListener('unhandledrejection', (event) => {
    if (!isCognitoRefreshSessionSupersededError(event.reason)) return
    event.preventDefault()
    notifySessionSuperseded()
  })
}

/** Test helper only. */
export function resetSessionSupersededRejectionHandlerForTests(): void {
  rejectionHandlerInstalled = false
}
