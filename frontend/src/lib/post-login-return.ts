/**
 * Same-origin SPA return path for Cognito Hosted UI: OAuth redirects to `/`,
 * so we persist the pre-login path in sessionStorage and restore it after sign-in.
 */

export const POST_LOGIN_RETURN_TO_KEY = 'smc:returnTo'

/**
 * Returns a safe relative path for in-SPA navigation, or null if unsafe / disallowed.
 * Mitigates open-redirect style abuse via sessionStorage tampering.
 */
export function sanitizeReturnPath(raw: string): string | null {
  const t = raw.trim()
  if (!t.startsWith('/')) return null
  if (t.startsWith('//')) return null
  if (t.includes('\\')) return null
  if (t === '/login' || t.startsWith('/login?') || t.startsWith('/login#')) return null
  return t
}

/** Call immediately before `signInWithRedirect` to capture the current location. */
export function persistReturnPathBeforeHostedUi(): void {
  const raw = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const sanitized = sanitizeReturnPath(raw)
  if (!sanitized) return
  sessionStorage.setItem(POST_LOGIN_RETURN_TO_KEY, sanitized)
}

