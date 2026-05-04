import { Amplify } from 'aws-amplify'

import { cognitoHostedUiEnvComplete } from './cognito-hosted-ui-env'

/**
 * Public SPAs use Cognito Hosted UI / OAuth only. Native Amplify `loginWith.email`
 * is intentionally not configured.
 */

/**
 * Returns true when pool id, SPA client id, and Hosted UI domain are all set (trimmed non-empty).
 * Matches the build-time contract in `scripts/check-cognito-spa-env.mjs`.
 */
export function isAuthConfigured(): boolean {
  const poolId = import.meta.env.VITE_COGNITO_USER_POOL_ID as string | undefined
  const clientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID as string | undefined
  const domain = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined
  return cognitoHostedUiEnvComplete(poolId, clientId, domain)
}

/** Call once at app startup (each entry: student-main / teacher-main). */
export function configureAmplify(): void {
  if (!isAuthConfigured()) {
    return
  }

  const userPoolId = String(import.meta.env.VITE_COGNITO_USER_POOL_ID).trim()
  const userPoolClientId = String(import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID).trim()
  const oauthDomain = String(import.meta.env.VITE_COGNITO_DOMAIN).trim()

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          oauth: {
            domain: oauthDomain,
            scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
            redirectSignIn: [`${window.location.origin}/`],
            redirectSignOut: [`${window.location.origin}/`],
            responseType: 'code' as const,
          },
        },
      },
    },
  })
}
