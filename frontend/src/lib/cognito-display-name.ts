import { fetchAuthSession } from 'aws-amplify/auth'
import { useEffect, useState } from 'react'

const PROFILE_CLAIM_KEYS = ['email', 'given_name', 'name', 'nickname', 'preferred_username'] as const

function pickStringClaims(
  payload: Record<string, unknown> | undefined,
): Partial<Record<(typeof PROFILE_CLAIM_KEYS)[number], string | undefined>> {
  const out: Partial<Record<(typeof PROFILE_CLAIM_KEYS)[number], string | undefined>> = {}
  if (!payload) return out
  for (const key of PROFILE_CLAIM_KEYS) {
    const v = payload[key]
    if (typeof v === 'string' && v.trim()) {
      out[key] = v.trim()
    }
  }
  return out
}

/**
 * Cognito Hosted UI + Google: derive profile fields from the **ID token** only.
 * We intentionally do **not** call `fetchUserAttributes()` (Cognito GetUser): it posts to
 * `cognito-idp` and returns 400 / NotAuthorized for common OAuth scope sets, and the
 * browser logs a failed request even when errors are caught. OpenID scopes already put
 * `email` / `name` / `given_name` (etc.) on the ID token for display.
 *
 * Optional `poolAttrs` supports tests (and any future caller) merging pool-shaped fields
 * without calling Cognito GetUser. Production calls use the default `{}`.
 */
export async function loadMergedProfileAttributes(
  poolAttrs: Partial<Record<string, string | undefined>> = {},
): Promise<Partial<Record<string, string | undefined>>> {
  const session = await fetchAuthSession().catch(() => undefined)

  const payload = session?.tokens?.idToken?.payload as Record<string, unknown> | undefined
  const fromToken = pickStringClaims(payload)

  const attrs = poolAttrs
  const merged: Partial<Record<string, string | undefined>> = { ...fromToken, ...attrs }
  // Pool attributes sometimes arrive as empty strings and would wipe federated IdP claims from the ID token.
  const poolByKey = attrs as Record<string, string | undefined>
  for (const key of PROFILE_CLAIM_KEYS) {
    const poolVal = poolByKey[key]
    const tokenVal = fromToken[key]
    const poolEmpty = !poolVal || !String(poolVal).trim()
    const tokenNonEmpty = tokenVal && String(tokenVal).trim()
    if (poolEmpty && tokenNonEmpty) {
      merged[key] = String(tokenVal).trim()
    }
  }

  return merged
}

function emailLocalPart(email: string): string {
  const i = email.indexOf('@')
  return i > 0 ? email.slice(0, i) : email
}

/**
 * Human-readable label for the signed-in user. Cognito federated Google users
 * often have an opaque `username` like `Google_<sub>`; prefer IdP attributes when present.
 */
export function displayNameFromAttributes(
  attrs: Partial<Record<string, string | undefined>>,
  username: string,
): string {
  const given = attrs.given_name?.trim()
  if (given) return given

  const fullName = attrs.name?.trim()
  if (fullName) {
    const first = fullName.split(/\s+/).find((w) => w.length > 0)
    if (first) return first
  }

  const email = attrs.email?.trim()
  if (email) {
    if (username.includes('@')) {
      return emailLocalPart(username)
    }
    return emailLocalPart(email)
  }

  return username
}

type CognitoDisplayName = {
  label: string
  /** Full hint for tooltips (email or username). */
  title: string
  /** False while resolving attributes — avoids flashing the raw Cognito `Google_…` username. */
  ready: boolean
}

/**
 * Loads Cognito user attributes and derives a short display label (e.g. given name for Google users).
 */
export function useCognitoDisplayName(username: string | undefined): CognitoDisplayName {
  const [state, setState] = useState<CognitoDisplayName>(() => ({
    label: '',
    title: '',
    ready: username == null || username === '',
  }))

  useEffect(() => {
    if (!username) {
      setState({ label: '', title: '', ready: true })
      return
    }

    setState({ label: '', title: '', ready: false })

    let cancelled = false
    void (async () => {
      try {
        const attrs = await loadMergedProfileAttributes()
        if (cancelled) return
        const label = displayNameFromAttributes(attrs, username)
        const title = attrs.email?.trim() || username
        setState({ label, title, ready: true })
      } catch {
        if (cancelled) return
        const label = displayNameFromAttributes({}, username)
        setState({ label, title: username, ready: true })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [username])

  return state
}
