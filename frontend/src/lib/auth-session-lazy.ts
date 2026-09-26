/**
 * Lazy auth session probe for public-route chrome (Amplify loads on demand).
 * No static top-level imports from aws-amplify.
 */

import { clearClientAuthState } from './clear-client-auth-state'
import { isStudentSessionSuperseded } from './student-session-superseded-state'

let profileWarmDone = false
let amplifyConfigured = false
/** Successful label only. Failures stay uncached so the next probe can retry. */
let cachedProfileDisplayName: string | undefined
/** Bumped on sign-out so an in-flight lookup cannot repopulate the cache. */
let profileNameEpoch = 0

/** Reset warm state (e.g. after sign-out). */
export function resetProfileWarmState(): void {
  profileWarmDone = false
  amplifyConfigured = false
  cachedProfileDisplayName = undefined
  profileNameEpoch += 1
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

type ProbeSignedInOptions = {
  /** Allow token probe while supersede handling is active (Hub re-login verification). */
  bypassSupersedeCheck?: boolean
}

/** True when Cognito is configured and the user has an ID token (signed in). */
export async function probeSignedIn(options?: ProbeSignedInOptions): Promise<boolean> {
  if (!options?.bypassSupersedeCheck && isStudentSessionSuperseded()) return false
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
  if (isStudentSessionSuperseded()) return
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

/**
 * Resolve a short profile label for chrome (ProfileMenu). Uses /users/me email plus
 * ID-token claims via cognito-display-name (dynamic import only). Cached until reset.
 */
export async function getProfileDisplayNameOnce(): Promise<string | null> {
  if (isStudentSessionSuperseded()) return null
  if (cachedProfileDisplayName !== undefined) return cachedProfileDisplayName
  const epoch = profileNameEpoch
  if (!(await ensureAmplifyConfigured())) return null
  if (epoch !== profileNameEpoch || isStudentSessionSuperseded()) return null

  try {
    const [{ fetchMe }, { loadMergedProfileAttributes, displayNameFromAttributes }] =
      await Promise.all([import('./api/session'), import('./cognito-display-name')])

    let email = ''
    try {
      const me = await fetchMe()
      email = typeof me.email === 'string' ? me.email.trim() : ''
    } catch {
      // Token claims alone may still yield a label.
    }

    if (epoch !== profileNameEpoch || isStudentSessionSuperseded()) return null

    const poolAttrs = email ? { email } : {}
    const attrs = await loadMergedProfileAttributes(poolAttrs)
    if (epoch !== profileNameEpoch || isStudentSessionSuperseded()) return null

    const label = displayNameFromAttributes(attrs, email).trim()
    if (!label || epoch !== profileNameEpoch) return null
    cachedProfileDisplayName = label
    return label
  } catch {
    return null
  }
}

export async function lazySignOut(): Promise<void> {
  resetProfileWarmState()
  const skipAmplifySignOut = isStudentSessionSuperseded()
  try {
    if (skipAmplifySignOut || !(await ensureAmplifyConfigured())) return
    const { signOut } = await import('aws-amplify/auth')
    await signOut()
  } catch {
    /* Stale refresh deny can block signOut; storage wipe still runs in finally. */
  } finally {
    const { releaseStudentSessionRefreshRegistration } = await import('./student-session-refresh')
    releaseStudentSessionRefreshRegistration()
    clearClientAuthState()
  }
}
