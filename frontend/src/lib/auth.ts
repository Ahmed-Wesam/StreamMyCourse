import { Amplify } from 'aws-amplify'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'
import { CookieStorage, defaultStorage } from 'aws-amplify/utils'

import { AUTH_REMEMBER_ME_FLAG } from './clear-amplify-auth-caches'
import { isAuthConfigured } from './is-auth-configured'

export { isAuthConfigured }

/** Student SPA: Google OAuth plus native email/password via Amplify Auth APIs. */

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

/**
 * Amplify's CookieStorage defaults `expires` to 365 days unless the key is present.
 * Pass `expires: undefined` so the cookie is a session cookie (no Max-Age / Expires).
 */
function sessionCookieStorage(): CookieStorage {
  return new CookieStorage({
    secure: true,
    sameSite: 'lax',
    expires: undefined,
  })
}

function writeRememberMeFlag(value: 'session' | 'remember' | null): void {
  try {
    if (value === null) localStorage.removeItem(AUTH_REMEMBER_ME_FLAG)
    else localStorage.setItem(AUTH_REMEMBER_ME_FLAG, value)
  } catch {
    /* ignore */
  }
}

/** True when the last email/password sign-in checked Remember me. */
export function isRememberMeSelected(): boolean {
  try {
    return localStorage.getItem(AUTH_REMEMBER_ME_FLAG) === 'remember'
  } catch {
    return false
  }
}

/**
 * Email/password sign-in. Unchecked stores tokens in session cookies.
 * Checked keeps Amplify's default storage (localStorage when available).
 */
export function applyRememberMeStorage(remember: boolean): void {
  writeRememberMeFlag(remember ? 'remember' : 'session')
  cognitoUserPoolsTokenProvider.setKeyValueStorage(remember ? defaultStorage : sessionCookieStorage())
}

/** Google has no Remember me checkbox. Always use default storage and drop a session-only flag. */
export function keepDefaultAuthStorage(): void {
  writeRememberMeFlag(null)
  cognitoUserPoolsTokenProvider.setKeyValueStorage(defaultStorage)
}

/** Select storage from the persisted flag before Amplify reads tokens. */
function applyPersistedAuthStorage(): void {
  let flag: string | null = null
  try {
    flag = localStorage.getItem(AUTH_REMEMBER_ME_FLAG)
  } catch {
    flag = null
  }
  if (flag === 'session') {
    cognitoUserPoolsTokenProvider.setKeyValueStorage(sessionCookieStorage())
  }
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

  applyPersistedAuthStorage()

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
          email: true,
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
