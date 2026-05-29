/** Substrings from Cognito Pre Token deny (session_sync.py StudentSessionSupersededError). */
const REFRESH_SUPERSEDED_MARKERS = [
  'student refresh session superseded',
  'client_metadata_session_id_vs_rds_active',
] as const

function collectErrorText(error: unknown, depth = 0): string {
  if (depth > 4 || error == null) return ''
  const parts: string[] = []

  if (typeof error === 'string') {
    parts.push(error)
  } else if (error instanceof Error) {
    parts.push(error.name, error.message)
    const cause = (error as Error & { cause?: unknown }).cause
    if (cause !== undefined) {
      parts.push(collectErrorText(cause, depth + 1))
    }
  } else if (typeof error === 'object') {
    const record = error as Record<string, unknown>
    for (const key of ['name', 'message', 'code', 'underlyingError', 'recoverySuggestion']) {
      const value = record[key]
      if (typeof value === 'string' && value.trim()) {
        parts.push(value)
      }
    }
    const nested = record.cause ?? record.underlyingException
    if (nested !== undefined) {
      parts.push(collectErrorText(nested, depth + 1))
    }
  } else {
    parts.push(String(error))
  }

  return parts.join(' ')
}

/**
 * True when Cognito refused a student refresh because clientMetadata session id
 * does not match RDS (single-session). Do not treat generic network/SDK errors as superseded.
 */
export function isCognitoRefreshSessionSupersededError(error: unknown): boolean {
  const text = collectErrorText(error).toLowerCase()
  if (!text) return false

  return REFRESH_SUPERSEDED_MARKERS.some((marker) => text.includes(marker))
}
