import { fetchAuthSession } from 'aws-amplify/auth'
import { cognitoUserPoolsTokenProvider, tokenOrchestrator } from 'aws-amplify/auth/cognito'

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
  const tokens = await tokenOrchestrator.getTokenStore().loadTokens()
  const sessionId = studentSessionIdFromIdToken(tokens?.idToken ?? undefined)
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
  cognitoUserPoolsTokenProvider.setClientMetadataProvider(clientMetadataFromStoredTokens)
}

/** ClientMetadata for an explicit fetchAuthSession force refresh. */
export async function buildStudentRefreshClientMetadata(): Promise<Record<string, string>> {
  return clientMetadataFromStoredTokens()
}

/** Reset registration flag — test helper only. */
export function resetStudentSessionRefreshRegistrationForTests(): void {
  providerRegistered = false
}
