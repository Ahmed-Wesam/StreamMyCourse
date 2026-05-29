/**
 * While the student SPA is handling session_superseded, skip Amplify session fetches
 * so stale refresh metadata does not re-enter Cognito deny loops and freeze the tab.
 */
let handling = false

export function isSessionSupersedeHandling(): boolean {
  return handling
}

export function armSessionSupersedeHandling(): void {
  handling = true
}

export function clearSessionSupersedeHandling(): void {
  handling = false
}

/** Test helper only. */
export function resetSessionSupersedeHandlingForTests(): void {
  handling = false
}
