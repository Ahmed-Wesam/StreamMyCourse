import { signInWithRedirect } from 'aws-amplify/auth'

import { keepDefaultAuthStorage } from './auth'
import { saveGoogleOAuthTermsAck } from './google-oauth-terms'
import { persistReturnPathBeforeHostedUi } from './post-login-return'

/** Google sign-in from login (returning users; no pre-redirect terms ack). */
export function beginStudentGoogleSignInForLogin(): void {
  keepDefaultAuthStorage()
  persistReturnPathBeforeHostedUi()
  void signInWithRedirect({ provider: 'Google' })
}

/** Google sign-in from register after terms acceptance; persists ack for post-OAuth PATCH. */
export function beginStudentGoogleSignInFromRegister(
  termsAccepted: boolean,
  privacyAccepted: boolean,
): void {
  if (!termsAccepted || !privacyAccepted) {
    return
  }
  keepDefaultAuthStorage()
  persistReturnPathBeforeHostedUi()
  saveGoogleOAuthTermsAck()
  void signInWithRedirect({ provider: 'Google' })
}
