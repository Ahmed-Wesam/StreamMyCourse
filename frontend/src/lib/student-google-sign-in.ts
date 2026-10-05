import { signInWithRedirect } from 'aws-amplify/auth'

import { keepDefaultAuthStorage } from './auth'
import { saveGoogleOAuthTermsAck } from './google-oauth-terms'
import { persistReturnPathBeforeHostedUi } from './post-login-return'

/** Hosted UI Google sign-in for students (requires terms acceptance before redirect). */
export function beginStudentGoogleSignIn(termsAccepted: boolean, privacyAccepted: boolean): void {
  if (!termsAccepted || !privacyAccepted) {
    return
  }
  keepDefaultAuthStorage()
  persistReturnPathBeforeHostedUi()
  saveGoogleOAuthTermsAck()
  void signInWithRedirect({ provider: 'Google' })
}
