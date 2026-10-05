/** Terms acceptance captured before Cognito Hosted UI (Google sign-up / first Google sign-in). */

export const GOOGLE_OAUTH_TERMS_ACK_KEY = 'rs_google_oauth_terms_ack'

type GoogleOAuthTermsAck = {
  termsAcceptedAt: string
  privacyAcceptedAt: string
}

export function saveGoogleOAuthTermsAck(now: string = new Date().toISOString()): void {
  const ack: GoogleOAuthTermsAck = {
    termsAcceptedAt: now,
    privacyAcceptedAt: now,
  }
  sessionStorage.setItem(GOOGLE_OAUTH_TERMS_ACK_KEY, JSON.stringify(ack))
}

export function readGoogleOAuthTermsAck(): GoogleOAuthTermsAck | null {
  try {
    const raw = sessionStorage.getItem(GOOGLE_OAUTH_TERMS_ACK_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as GoogleOAuthTermsAck
    if (
      !parsed ||
      typeof parsed.termsAcceptedAt !== 'string' ||
      typeof parsed.privacyAcceptedAt !== 'string'
    ) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function clearGoogleOAuthTermsAck(): void {
  sessionStorage.removeItem(GOOGLE_OAUTH_TERMS_ACK_KEY)
}
