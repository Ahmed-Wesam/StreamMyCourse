import { fetchAuthSession } from 'aws-amplify/auth'

import { notifySessionSuperseded } from '../handleSessionSuperseded'

const API_BASE_URL_RAW = import.meta.env.VITE_API_BASE_URL as string | undefined

/** Catalog API error code when the student session was superseded by a newer sign-in. */
export const SESSION_SUPERSEDED = 'session_superseded'

export class ApiError extends Error {
  readonly status: number
  readonly code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function failedResponseError(res: Response): Promise<ApiError> {
  let message = `Request failed: ${res.status}`
  let code: string | undefined
  try {
    const j = (await res.json()) as { message?: string; code?: string }
    if (typeof j.message === 'string' && j.message.trim()) message = j.message.trim()
    if (typeof j.code === 'string' && j.code.trim()) code = j.code.trim()
  } catch {
    /* ignore non-JSON */
  }
  return new ApiError(message, res.status, code)
}

async function raiseResponseError(res: Response): Promise<never> {
  const err = await failedResponseError(res)
  if (isSessionSupersededError(err)) {
    notifySessionSuperseded()
  }
  throw err
}

async function refreshAuthSession() {
  const { buildStudentRefreshClientMetadata } = await import('../student-session-refresh')
  const clientMetadata = await buildStudentRefreshClientMetadata()
  if (Object.keys(clientMetadata).length > 0) {
    return fetchAuthSession({ forceRefresh: true, clientMetadata })
  }
  return fetchAuthSession({ forceRefresh: true })
}

/** True when the catalog API refused the request because the student signed in elsewhere. */
export function isSessionSupersededError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.code === SESSION_SUPERSEDED
}

/**
 * True when the catalog API refused lesson/playback access because the user lacks a subscription.
 */
export function isSubscriptionRequiredError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'subscription_required') return true
  return false
}

/**
 * True when the catalog API refused lesson/playback access because the user is not enrolled.
 * Prefer `code: enrollment_required`; fall back to 403 + message for proxies or older payloads.
 */
export function isEnrollmentRequiredError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'enrollment_required') return true
  if (e.status === 403 && /enrollment/i.test(e.message)) return true
  return false
}

/** Subscription or legacy enrollment gate — show enroll / subscribe affordance. */
export function isCourseAccessDeniedError(e: unknown): boolean {
  return isSubscriptionRequiredError(e) || isEnrollmentRequiredError(e)
}

/**
 * True when progress tracking is unavailable because RDS is not configured.
 * The API returns 503 with code `progress_requires_rds`.
 */
export function isProgressRdsUnavailableError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.status === 503 && e.code === 'progress_requires_rds') return true
  return false
}

/**
 * True when playback was denied because the caller is not authenticated
 * (missing or rejected token at the gateway, or Lambda `unauthorized`).
 */
export function isPlaybackAuthRequiredError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (isSessionSupersededError(e)) return false
  if (e.status === 401) return true
  if (e.code === 'unauthorized') return true
  return false
}

/** True when module deletion failed because the course must keep at least one module. */
export function isLastModuleDeleteError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'last_module_required' && e.status === 400) return true
  if (e.status === 400 && /last module/i.test(e.message)) return true
  return false
}

/** True when module deletion is blocked because the media cleanup queue is not configured. */
export function isMediaCleanupUnavailableError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'media_cleanup_unavailable' && e.status === 503) return true
  if (e.status === 503 && /media cleanup/i.test(e.message)) return true
  return false
}

/** True when billing checkout is unavailable (payments stack not configured). */
export function isBillingUnconfiguredError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 503 && e.code === 'billing_unconfigured'
}

/** True when checkout is blocked because the student already has a blocking subscription row. */
export function isAlreadySubscribedError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 409 && e.code === 'already_subscribed'
}

/** True when a recent incomplete checkout reservation is still open (double-click / in-flight HPP). */
export function isCheckoutInProgressError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 409 && e.code === 'checkout_in_progress'
}

/** True when GET /billing/subscription has no manageable subscription (WS7 manage contract). */
export function isNotSubscribedError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 404 && e.code === 'not_subscribed'
}

/** True when cancel-at-period-end was already applied. */
export function isAlreadyCanceledError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 409 && e.code === 'already_canceled'
}

/** True when POST cancel-subscription cannot apply in the current RDS state. */
export function isCannotCancelError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 409 && e.code === 'cannot_cancel'
}

/** True when catalog cancel succeeded but PayTabs cancel_agreement failed (WS8 manage contract). */
export function isProviderCancelFailedError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 502 && e.code === 'provider_cancel_failed'
}

/** True when cancel succeeded in RDS but no provider agreement id exists to call PayTabs. */
export function isProviderAgreementMissingError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  return e.status === 502 && e.code === 'provider_agreement_missing'
}

export function requireApiBaseUrl(): string {
  const base = API_BASE_URL_RAW?.trim()
  if (!base) {
    // Unit tests exercise request shape (path, headers, body). They don't require a real API base URL.
    if (import.meta.env.MODE === 'test') return 'https://example.test'
    throw new Error(
      'VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env and set the API base URL.',
    )
  }
  return base
}

export function bearerFromSession(session: Awaited<ReturnType<typeof fetchAuthSession>>): string | undefined {
  const id = session.tokens?.idToken as unknown
  if (id === undefined || id === null) return undefined
  if (typeof id === 'string') {
    const t = id.trim()
    return t || undefined
  }
  const s =
    typeof (id as { toString?: () => string }).toString === 'function'
      ? (id as { toString: () => string }).toString()
      : ''
  const trimmed = s.trim()
  if (!trimmed || trimmed === '[object Object]') return undefined
  return trimmed
}

async function authHeader(): Promise<Record<string, string>> {
  try {
    let session = await fetchAuthSession()
    let token = bearerFromSession(session)
    if (!token) {
      try {
        session = await refreshAuthSession()
        token = bearerFromSession(session)
      } catch {
        const { buildStudentRefreshClientMetadata, STUDENT_SESSION_METADATA_KEY } = await import(
          '../student-session-refresh',
        )
        const meta = await buildStudentRefreshClientMetadata()
        if (meta[STUDENT_SESSION_METADATA_KEY]) {
          notifySessionSuperseded()
        }
      }
    }
    if (!token) return {}
    return { Authorization: `Bearer ${token}` }
  } catch {
    return {}
  }
}

export async function mergeHeaders(base?: HeadersInit): Promise<Headers> {
  const h = new Headers(base)
  const auth = await authHeader()
  if (auth.Authorization) {
    h.set('Authorization', auth.Authorization)
  }
  return h
}

export async function httpGet<T>(path: string): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ Accept: 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: 'no-store', headers })
  if (!res.ok) {
    await raiseResponseError(res)
  }
  return (await res.json()) as T
}

/** Authenticated GET against the catalog API (for domain-specific clients such as billing). */
export async function catalogGet<T>(path: string): Promise<T> {
  return httpGet<T>(path)
}

export async function httpPost<T>(path: string, body: unknown): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    cache: 'no-store',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    await raiseResponseError(res)
  }
  return (await res.json()) as T
}

export async function httpPatch<T>(path: string, body: unknown): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    cache: 'no-store',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    await raiseResponseError(res)
  }
  return (await res.json()) as T
}

export async function httpPut<T>(path: string, body?: unknown): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    cache: 'no-store',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    await raiseResponseError(res)
  }
  return (await res.json()) as T
}

export async function httpDelete<T>(path: string): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ Accept: 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    cache: 'no-store',
    headers,
  })
  if (!res.ok) {
    await raiseResponseError(res)
  }
  return (await res.json()) as T
}
