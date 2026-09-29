/**
 * Authenticated Research Team API:
 * - Student: GET /me/research-team, POST /me/research-team/applications
 */

import { httpGet, httpPost } from './client'

export type ResearchTeamExperienceLevel = 'None' | 'Beginner' | 'Intermediate' | 'Advanced'

export type ResearchTeamWeeklyHours =
  | 'Less than 5 hours/week'
  | '5–10 hours/week'
  | '10–15 hours/week'
  | '15–20 hours/week'
  | '20+ hours/week'

export type ResearchTeamApplicationStatus =
  | 'submitted'
  | 'under_review'
  | 'accepted'
  | 'rejected'

type ResearchTeamMeCourse = {
  courseId: string
  title: string
  certified: boolean
}

export type ResearchTeamApplication = {
  id: string
  status: ResearchTeamApplicationStatus
  reapplyAllowed: boolean
  submittedAt: string
  fullName: string
  email: string
  country: string
  institution: string
  position: string
  publicationCount: number
  projectCount: number
  statsExperience: ResearchTeamExperienceLevel
  sysReviewExperience: ResearchTeamExperienceLevel
  researchAreas: string[]
  interests: string
  motivation: string
  weeklyHours: ResearchTeamWeeklyHours
  acknowledgedAt: string
}

type MeResearchTeamResponse = {
  courses: ResearchTeamMeCourse[]
  eligible: boolean
  canSubmit: boolean
  application: ResearchTeamApplication | null
}

export type SubmitResearchTeamApplicationBody = {
  fullName: string
  country: string
  institution: string
  position: string
  publicationCount: number
  projectCount: number
  statsExperience: ResearchTeamExperienceLevel
  sysReviewExperience: ResearchTeamExperienceLevel
  interests: string
  motivation: string
  weeklyHours: ResearchTeamWeeklyHours
  acknowledgement: true
  researchAreas?: string[]
}

export const RESEARCH_TEAM_EXPERIENCE_LEVELS: readonly ResearchTeamExperienceLevel[] = [
  'None',
  'Beginner',
  'Intermediate',
  'Advanced',
] as const

/** Display labels use an en dash (U+2013) between hour ranges. */
export const RESEARCH_TEAM_WEEKLY_HOURS: readonly ResearchTeamWeeklyHours[] = [
  'Less than 5 hours/week',
  '5–10 hours/week',
  '10–15 hours/week',
  '15–20 hours/week',
  '20+ hours/week',
] as const

export const RESEARCH_TEAM_AREAS: readonly string[] = [
  'General Surgery',
  'Plastic Surgery',
  'Vascular Surgery',
  'Internal Medicine',
  'Cardiology',
  'Oncology',
  'Public Health',
  'Medical Education',
  'Epidemiology',
  'Systematic Reviews & Meta-Analysis',
  'Clinical Research',
  'Basic Science Research',
  'Artificial Intelligence In Healthcare',
  'Other',
] as const

function normalizeStatus(value: unknown): ResearchTeamApplicationStatus {
  if (
    value === 'submitted' ||
    value === 'under_review' ||
    value === 'accepted' ||
    value === 'rejected'
  ) {
    return value
  }
  return 'submitted'
}

function normalizeExperience(value: unknown): ResearchTeamExperienceLevel {
  if (
    value === 'None' ||
    value === 'Beginner' ||
    value === 'Intermediate' ||
    value === 'Advanced'
  ) {
    return value
  }
  return 'None'
}

function normalizeWeeklyHours(value: unknown): ResearchTeamWeeklyHours {
  if (
    typeof value === 'string' &&
    (RESEARCH_TEAM_WEEKLY_HOURS as readonly string[]).includes(value)
  ) {
    return value as ResearchTeamWeeklyHours
  }
  return 'Less than 5 hours/week'
}

function normalizeMeCourse(row: unknown): ResearchTeamMeCourse | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const courseId = typeof record.courseId === 'string' ? record.courseId.trim() : ''
  if (!courseId) return null
  return {
    courseId,
    title: typeof record.title === 'string' ? record.title : '',
    certified: record.certified === true,
  }
}

function normalizeApplication(row: unknown): ResearchTeamApplication | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const id = typeof record.id === 'string' ? record.id.trim() : ''
  if (!id) return null
  const researchAreas = Array.isArray(record.researchAreas)
    ? record.researchAreas.filter((item): item is string => typeof item === 'string')
    : []
  return {
    id,
    status: normalizeStatus(record.status),
    reapplyAllowed: record.reapplyAllowed === true,
    submittedAt: typeof record.submittedAt === 'string' ? record.submittedAt : '',
    fullName: typeof record.fullName === 'string' ? record.fullName : '',
    email: typeof record.email === 'string' ? record.email : '',
    country: typeof record.country === 'string' ? record.country : '',
    institution: typeof record.institution === 'string' ? record.institution : '',
    position: typeof record.position === 'string' ? record.position : '',
    publicationCount: typeof record.publicationCount === 'number' ? record.publicationCount : 0,
    projectCount: typeof record.projectCount === 'number' ? record.projectCount : 0,
    statsExperience: normalizeExperience(record.statsExperience),
    sysReviewExperience: normalizeExperience(record.sysReviewExperience),
    researchAreas,
    interests: typeof record.interests === 'string' ? record.interests : '',
    motivation: typeof record.motivation === 'string' ? record.motivation : '',
    weeklyHours: normalizeWeeklyHours(record.weeklyHours),
    acknowledgedAt: typeof record.acknowledgedAt === 'string' ? record.acknowledgedAt : '',
  }
}

export async function getMyResearchTeam(): Promise<MeResearchTeamResponse> {
  const raw = await httpGet<Record<string, unknown>>('/me/research-team')
  const courses = Array.isArray(raw.courses)
    ? raw.courses.map(normalizeMeCourse).filter((item): item is ResearchTeamMeCourse => item !== null)
    : []
  return {
    courses,
    eligible: raw.eligible === true,
    canSubmit: raw.canSubmit === true,
    application: normalizeApplication(raw.application),
  }
}

export async function submitResearchTeamApplication(
  body: SubmitResearchTeamApplicationBody,
): Promise<ResearchTeamApplication> {
  const raw = await httpPost<Record<string, unknown>>('/me/research-team/applications', body)
  const application = normalizeApplication(raw)
  if (!application) {
    throw new Error('Failed to submit research team application: invalid response')
  }
  return application
}
