/**
 * Anonymous published-course catalog for marketing pages.
 * Does not import Amplify or the authenticated API client.
 */

export type PublicCatalogCourse = {
  id: string
  title: string
  description: string
  /** Present only when the API returned an https: URL. */
  thumbnailUrl?: string
}

function requirePublicApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || !base.trim()) {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

function isHttpsUrl(value: unknown): value is string {
  if (typeof value !== 'string' || !value) return false
  try {
    return new URL(value).protocol === 'https:'
  } catch {
    return false
  }
}

function mapPublishedRow(row: unknown): PublicCatalogCourse | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  if (record.status !== 'PUBLISHED') return null

  const id = typeof record.id === 'string' ? record.id.trim() : ''
  if (!id) return null

  const title = typeof record.title === 'string' ? record.title : ''
  const description = typeof record.description === 'string' ? record.description : ''

  const course: PublicCatalogCourse = { id, title, description }
  if (isHttpsUrl(record.thumbnailUrl)) {
    course.thumbnailUrl = record.thumbnailUrl
  }
  return course
}

/**
 * Fetch published courses without auth cookies or Authorization headers.
 * Empty array is success. Non-OK HTTP and non-JSON bodies throw Error.
 */
export async function listPublishedCourses(): Promise<PublicCatalogCourse[]> {
  const base = requirePublicApiBaseUrl()
  const response = await fetch(`${base}/courses`, {
    method: 'GET',
    credentials: 'omit',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Failed to load courses (${response.status})`)
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new Error('Failed to load courses: invalid JSON')
  }

  if (!Array.isArray(body)) {
    throw new Error('Failed to load courses: expected an array')
  }

  const courses: PublicCatalogCourse[] = []
  for (const row of body) {
    const mapped = mapPublishedRow(row)
    if (mapped) courses.push(mapped)
  }
  return courses
}
