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
  /** USD cents when the API includes pricing (RS-5). */
  amountMinor?: number
  currency?: string
  /** Present when the authenticated catalog includes access flags. */
  hasAccess?: boolean
  /** RS-7 catalog card meta from course page content. */
  level?: string
  estimatedHours?: number
  catalogSkills?: string[]
}

function normalizeCatalogLevel(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return trimmed ? trimmed : undefined
}

function normalizeEstimatedHours(value: unknown): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) return undefined
  const hours = Math.trunc(value)
  if (hours < 1 || hours > 200) return undefined
  return hours
}

function normalizeCatalogSkills(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined
  const skills = value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter(Boolean)
  return skills.length > 0 ? skills : undefined
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
  const amountRaw = record.amountMinor ?? record.amount_minor ?? record.priceAmountMinor ?? record.price_amount_minor
  if (typeof amountRaw === 'number' && Number.isFinite(amountRaw) && amountRaw > 0) {
    course.amountMinor = amountRaw
  }
  const currency = record.currency
  if (typeof currency === 'string' && currency.trim()) {
    course.currency = currency.trim()
  }
  if (record.hasAccess === true || record.enrolled === true) {
    course.hasAccess = true
  } else if (record.hasAccess === false || record.enrolled === false) {
    course.hasAccess = false
  }

  const level = normalizeCatalogLevel(record.level)
  if (level) course.level = level

  const estimatedHours = normalizeEstimatedHours(record.estimatedHours ?? record.estimated_hours)
  if (estimatedHours !== undefined) course.estimatedHours = estimatedHours

  const catalogSkills = normalizeCatalogSkills(record.catalogSkills ?? record.catalog_skills)
  if (catalogSkills) course.catalogSkills = catalogSkills

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
