/**
 * Anonymous contact form submit for marketing pages.
 * Does not import Amplify or the authenticated API client.
 */

type PublicContactPayload = {
  name: string
  email: string
  category: string
  subject: string
  message: string
  rs_hp?: string
}

type PublicContactOutcome =
  | 'accepted'
  | 'validation_error'
  | 'rate_limited'
  | 'unavailable'
  | 'unexpected'

function requirePublicApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || !base.trim()) {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

/**
 * POST /contact without auth cookies or Authorization headers.
 */
export async function submitPublicContact(
  payload: PublicContactPayload,
): Promise<PublicContactOutcome> {
  const base = requirePublicApiBaseUrl()
  const body: Record<string, string> = {
    name: payload.name,
    email: payload.email,
    category: payload.category,
    subject: payload.subject,
    message: payload.message,
  }
  const honeypot = payload.rs_hp?.trim()
  if (honeypot) {
    body.rs_hp = honeypot
  }

  const response = await fetch(`${base}/contact`, {
    method: 'POST',
    credentials: 'omit',
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 202) return 'accepted'
  if (response.status === 400) return 'validation_error'
  if (response.status === 429) return 'rate_limited'
  if (response.status === 503) return 'unavailable'
  return 'unexpected'
}
