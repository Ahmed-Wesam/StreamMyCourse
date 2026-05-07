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

function isDevLoopbackHostname(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1'
}

function originWithSlash(o: string): string {
  return `${o}/`
}

/** `location.href` is canonical; fall back for partial test stubs / edge runtimes. */
function currentLocationHref(): string {
  if (typeof window.location.href === 'string' && window.location.href.length > 0) {
    return window.location.href
  }
  return `${window.location.origin}${window.location.pathname || '/'}${window.location.search}${window.location.hash}`
}

/**
 * Hosted UI redirect URIs (must match Cognito app client callback URLs exactly).
 * Localhost vs 127.0.0.1 differ in `redirect_uri`; Cognito must list both.
 * Uses `URL` so implicit default ports (empty `location.port`) still match Cognito entries.
 */
function oauthRedirectUrls(): string[] {
  const origin = window.location.origin
  const urls = new Set<string>([originWithSlash(origin)])
  if (!import.meta.env.DEV) {
    return [...urls]
  }
  const { hostname, protocol } = window.location
  if (protocol !== 'http:' && protocol !== 'https:') {
    return [...urls]
  }
  if (!isDevLoopbackHostname(hostname)) {
    return [...urls]
  }
  try {
    const base = new URL(currentLocationHref())
    const onLocal = new URL(base.href)
    onLocal.hostname = 'localhost'
    urls.add(originWithSlash(onLocal.origin))
    const on127 = new URL(base.href)
    on127.hostname = '127.0.0.1'
    urls.add(originWithSlash(on127.origin))
  } catch {
    return [...urls]
  }
  return [...urls]
}

/** Call once at app startup (each entry: student-main / teacher-main). */
export function configureAmplify(): void {
  if (!isAuthConfigured()) {
    return
  }

  // Dev-only: OAuth redirect_uri must match Cognito allowlists; IPv6 loopback is not
  // reliably supported as a callback URL in all pools—normalize to 127.0.0.1 once.
  // Use `URL` so default ports (empty `location.port`) serialize correctly.
  if (import.meta.env.DEV) {
    const h = window.location.hostname
    if (h === '[::1]' || h === '::1') {
      const { protocol } = window.location
      if (protocol === 'http:' || protocol === 'https:') {
        try {
          const next = new URL(currentLocationHref())
          next.hostname = '127.0.0.1'
          window.location.replace(next.href)
          return
        } catch {
          // Fall through: configure Amplify with current location
        }
      }
    }
  }

  const userPoolId = String(import.meta.env.VITE_COGNITO_USER_POOL_ID).trim()
  const userPoolClientId = String(import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID).trim()
  const oauthDomain = String(import.meta.env.VITE_COGNITO_DOMAIN).trim()
  const redirects = oauthRedirectUrls()

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          oauth: {
            domain: oauthDomain,
            scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
            redirectSignIn: redirects,
            redirectSignOut: redirects,
            responseType: 'code' as const,
          },
        },
      },
    },
  })
}
