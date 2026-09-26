import { cognitoHostedUiEnvComplete } from './cognito-hosted-ui-env'

/**
 * Returns true when pool id, SPA client id, and Hosted UI domain are all set (trimmed non-empty).
 * Matches the build-time contract in `scripts/check-cognito-spa-env.mjs`.
 * Kept free of Amplify imports so public chrome can call it without pulling amplify-vendor.
 */
export function isAuthConfigured(): boolean {
  const poolId = import.meta.env.VITE_COGNITO_USER_POOL_ID as string | undefined
  const clientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID as string | undefined
  const domain = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined
  return cognitoHostedUiEnvComplete(poolId, clientId, domain)
}
