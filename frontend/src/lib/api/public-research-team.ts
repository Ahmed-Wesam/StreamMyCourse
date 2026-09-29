/**
 * Anonymous Research Team requirements (GET /research-team/requirements).
 * Does not import Amplify or the authenticated API client.
 */

export type ResearchTeamRequiredCourse = {
  id: string
  title: string
}

type ResearchTeamRequirementsResponse = {
  courses: ResearchTeamRequiredCourse[]
}

function requirePublicApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || !base.trim()) {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

function normalizeCourse(row: unknown): ResearchTeamRequiredCourse | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const id = typeof record.id === 'string' ? record.id.trim() : ''
  const title = typeof record.title === 'string' ? record.title.trim() : ''
  if (!id || !title) return null
  return { id, title }
}

/**
 * GET /research-team/requirements without auth cookies or Authorization headers.
 */
export async function getResearchTeamRequirements(): Promise<ResearchTeamRequirementsResponse> {
  const base = requirePublicApiBaseUrl()
  const response = await fetch(`${base}/research-team/requirements`, {
    method: 'GET',
    credentials: 'omit',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new Error(`Failed to load research team requirements (${response.status})`)
  }

  if (!response.ok) {
    throw new Error(`Failed to load research team requirements (${response.status})`)
  }

  if (!body || typeof body !== 'object') {
    throw new Error('Failed to load research team requirements: invalid JSON')
  }

  const record = body as Record<string, unknown>
  const courses = Array.isArray(record.courses)
    ? record.courses
        .map(normalizeCourse)
        .filter((item): item is ResearchTeamRequiredCourse => item !== null)
    : []

  return { courses }
}
