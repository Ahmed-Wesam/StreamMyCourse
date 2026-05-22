/**
 * Lazy auth session probe for public-route chrome (Amplify loads on demand).
 * No static top-level imports from aws-amplify.
 */

let profileWarmDone = false
let amplifyConfigured = false

/** Reset warm state (e.g. after sign-out). */
export function resetProfileWarmState(): void {
  profileWarmDone = false
  amplifyConfigured = false
}

/** Called after AuthShell bootstrap successfully warms /users/me. */
export function markUserProfileWarmed(): void {
  profileWarmDone = true
}

async function ensureAmplifyConfigured(): Promise<boolean> {
  const { isAuthConfigured, configureAmplify } = await import('./auth')
  if (!isAuthConfigured()) return false
  if (!amplifyConfigured) {
    configureAmplify()
    amplifyConfigured = true
  }
  return true
}

/** True when Cognito is configured and the user has an ID token (signed in). */
export async function probeSignedIn(): Promise<boolean> {
  if (!(await ensureAmplifyConfigured())) return false
  const { hasSignedInIdToken } = await import('./api/session')
  return hasSignedInIdToken()
}

/**
 * GET /users/me once per session when signed in on a public route (no AuthShell).
 * Mirrors StudentProfileBootstrap; non-fatal on failure.
 * @param alreadySignedIn Skip probe when caller already verified session (e.g. header idle probe).
 */
export async function warmUserProfileOnce(alreadySignedIn = false): Promise<void> {
  if (profileWarmDone) return
  if (!(await ensureAmplifyConfigured())) return
  if (!alreadySignedIn) {
    const signedIn = await probeSignedIn()
    if (!signedIn) return
  }
  profileWarmDone = true
  try {
    const { fetchMe } = await import('./api/session')
    await fetchMe()
  } catch {
    profileWarmDone = false
  }
}

export async function lazySignOut(): Promise<void> {
  resetProfileWarmState()
  if (!(await ensureAmplifyConfigured())) return
  const { signOut } = await import('aws-amplify/auth')
  await signOut()
}
