import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'

import { isStudentSessionSuperseded } from './student-session-superseded-state'

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
  if (isStudentSessionSuperseded()) return {}
  const tokens = await cognitoUserPoolsTokenProvider.authTokenStore.loadTokens()
  const sessionId = studentSessionIdFromIdToken(
    tokens?.idToken as IdTokenWithPayload | undefined,
  )
  return sessionId ? { [STUDENT_SESSION_METADATA_KEY]: sessionId } : {}
}

let providerRegistered = false

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

/** Reset registration flag — test helper only. */
export function resetStudentSessionRefreshRegistrationForTests(): void {
  releaseStudentSessionRefreshRegistration()
}
