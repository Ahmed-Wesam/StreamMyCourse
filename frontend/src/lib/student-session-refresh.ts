import { fetchAuthSession } from 'aws-amplify/auth'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'

import { isCognitoRefreshSessionSupersededError } from './cognito-session-superseded'
import { isSessionSupersedeHandling } from './session-supersede-handling'

/** Cognito Pre Token claim and ClientMetadata key (see session_sync.py). */
export const STUDENT_SESSION_METADATA_KEY = 'student_session_id'

type IdTokenWithPayload = {
  payload: Record<string, unknown>
  toString?: () => string
}

export function studentSessionIdFromIdToken(idToken: IdTokenWithPayload | undefined): string | undefined {
  if (!idToken) return undefined
  const payload = idToken.payload
  for (const key of [STUDENT_SESSION_METADATA_KEY, `custom:${STUDENT_SESSION_METADATA_KEY}`]) {
    const raw = payload[key]
    if (typeof raw === 'string' && raw.trim()) return raw.trim()
  }
  return undefined
}

async function clientMetadataFromStoredTokens(): Promise<Record<string, string>> {
  if (isSessionSupersedeHandling()) return {}
  try {
    const session = await fetchAuthSession()
    const sessionId = studentSessionIdFromIdToken(
      session.tokens?.idToken as IdTokenWithPayload | undefined,
    )
    return sessionId ? { [STUDENT_SESSION_METADATA_KEY]: sessionId } : {}
  } catch (error) {
    // Avoid Amplify refresh metadata provider re-entering a stale-session deny loop.
    if (isCognitoRefreshSessionSupersededError(error)) return {}
    throw error
  }
}

let providerRegistered = false

/** Stop refresh ClientMetadata reads while supersede sign-out runs (avoids Cognito deny loops). */
export function suspendStudentSessionRefreshMetadata(): void {
  try {
    cognitoUserPoolsTokenProvider.setClientMetadataProvider(async () => ({}))
  } catch {
    /* Amplify not configured (tests) */
  }
}

/** Re-attach session id metadata after dismiss or a verified new sign-in (Guard stays mounted). */
export function restoreStudentSessionRefreshMetadata(): void {
  if (!providerRegistered) return
  try {
    cognitoUserPoolsTokenProvider.setClientMetadataProvider(clientMetadataFromStoredTokens)
  } catch {
    /* Amplify not configured (tests) */
  }
}

/**
 * Attach student_session_id to Cognito refresh (GetTokensFromRefreshToken ClientMetadata).
 * Student SPA only — call once after Amplify is configured.
 */
export function registerStudentSessionRefreshMetadata(): void {
  if (providerRegistered) return
  providerRegistered = true
  try {
    cognitoUserPoolsTokenProvider.setClientMetadataProvider(clientMetadataFromStoredTokens)
  } catch {
    providerRegistered = false
  }
}

/** Allow registerStudentSessionRefreshMetadata after sign-out / storage wipe. */
export function releaseStudentSessionRefreshRegistration(): void {
  providerRegistered = false
}

/** ClientMetadata for an explicit fetchAuthSession force refresh. */
export async function buildStudentRefreshClientMetadata(): Promise<Record<string, string>> {
  return clientMetadataFromStoredTokens()
}

/** Reset registration flag — test helper only. */
export function resetStudentSessionRefreshRegistrationForTests(): void {
  releaseStudentSessionRefreshRegistration()
}
