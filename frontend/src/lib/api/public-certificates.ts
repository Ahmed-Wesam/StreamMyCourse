/**
 * Anonymous public certificate verification (GET /certificates/{credentialId}).
 * Does not import Amplify or the authenticated API client.
 */

type PublicCertificate = {
  credentialId: string
  status: 'valid' | 'revoked'
  studentName: string
  courseTitle: string
  /** Already-formatted issue label from the API. */
  issueDate: string
  instructorName?: string
  instructorTitle?: string
}

type PublicCertificateNotFound = {
  status: 'not_found'
  credentialId?: string
}

export type PublicCertificateResult = PublicCertificate | PublicCertificateNotFound

function requirePublicApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || !base.trim()) {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

/**
 * GET /certificates/{credentialId} without auth cookies or Authorization headers.
 */
export async function getPublicCertificate(credentialId: string): Promise<PublicCertificateResult> {
  const base = requirePublicApiBaseUrl()
  const id = credentialId.trim()
  const response = await fetch(`${base}/certificates/${encodeURIComponent(id)}`, {
    method: 'GET',
    credentials: 'omit',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new Error(`Failed to verify certificate (${response.status})`)
  }

  if (response.status === 404) {
    const record = body && typeof body === 'object' ? (body as Record<string, unknown>) : {}
    const result: PublicCertificateNotFound = { status: 'not_found' }
    if (typeof record.credentialId === 'string' && record.credentialId.trim()) {
      result.credentialId = record.credentialId.trim()
    }
    return result
  }

  if (!response.ok) {
    throw new Error(`Failed to verify certificate (${response.status})`)
  }

  if (!body || typeof body !== 'object') {
    throw new Error('Failed to verify certificate: invalid JSON')
  }

  const record = body as Record<string, unknown>
  const credential = typeof record.credentialId === 'string' ? record.credentialId.trim() : id
  const status = record.status === 'revoked' ? 'revoked' : 'valid'
  const result: PublicCertificate = {
    credentialId: credential,
    status,
    studentName: typeof record.studentName === 'string' ? record.studentName : '',
    courseTitle: typeof record.courseTitle === 'string' ? record.courseTitle : '',
    issueDate: typeof record.issueDate === 'string' ? record.issueDate : '',
  }
  if (typeof record.instructorName === 'string' && record.instructorName.trim()) {
    result.instructorName = record.instructorName.trim()
  }
  if (typeof record.instructorTitle === 'string' && record.instructorTitle.trim()) {
    result.instructorTitle = record.instructorTitle.trim()
  }
  return result
}
