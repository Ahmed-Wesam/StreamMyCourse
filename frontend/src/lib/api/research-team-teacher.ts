/**
 * Admin Research Team API (RS-14 instructor SPA):
 * - GET/PUT /courses/{courseId}/research-team-requirement
 * - GET /research-team/applications
 * - GET /research-team/applications/{id}
 * - PATCH /research-team/applications/{id} (status only)
 * - POST /research-team/applications/{id}/allow-reapply
 */

import { httpGet, httpPatch, httpPost, httpPut } from './client'
import type {
  ResearchTeamApplication,
  ResearchTeamApplicationStatus,
} from './research-team'

export type AdminResearchTeamApplication = ResearchTeamApplication & {
  userSub: string
}

type SetCourseResearchTeamRequirementResponse = {
  courseId: string
  required: boolean
}

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

function normalizeAdminApplication(row: unknown): AdminResearchTeamApplication | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const id = typeof record.id === 'string' ? record.id.trim() : ''
  if (!id) return null
  const researchAreas = Array.isArray(record.researchAreas)
    ? record.researchAreas.filter((item): item is string => typeof item === 'string')
    : []
  return {
    id,
    userSub: typeof record.userSub === 'string' ? record.userSub : '',
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
    statsExperience:
      record.statsExperience === 'None' ||
      record.statsExperience === 'Beginner' ||
      record.statsExperience === 'Intermediate' ||
      record.statsExperience === 'Advanced'
        ? record.statsExperience
        : 'None',
    sysReviewExperience:
      record.sysReviewExperience === 'None' ||
      record.sysReviewExperience === 'Beginner' ||
      record.sysReviewExperience === 'Intermediate' ||
      record.sysReviewExperience === 'Advanced'
        ? record.sysReviewExperience
        : 'None',
    researchAreas,
    interests: typeof record.interests === 'string' ? record.interests : '',
    motivation: typeof record.motivation === 'string' ? record.motivation : '',
    weeklyHours:
      typeof record.weeklyHours === 'string' ? (record.weeklyHours as AdminResearchTeamApplication['weeklyHours']) : 'Less than 5 hours/week',
    acknowledgedAt: typeof record.acknowledgedAt === 'string' ? record.acknowledgedAt : '',
  }
}

export async function getCourseResearchTeamRequirement(
  courseId: string,
): Promise<SetCourseResearchTeamRequirementResponse> {
  const res = await httpGet<SetCourseResearchTeamRequirementResponse>(
    `/courses/${encodeURIComponent(courseId)}/research-team-requirement`,
  )
  return {
    courseId: typeof res.courseId === 'string' ? res.courseId : courseId,
    required: res.required === true,
  }
}

export async function setCourseResearchTeamRequirement(
  courseId: string,
  required: boolean,
): Promise<SetCourseResearchTeamRequirementResponse> {
  const res = await httpPut<SetCourseResearchTeamRequirementResponse>(
    `/courses/${encodeURIComponent(courseId)}/research-team-requirement`,
    { required },
  )
  return {
    courseId: typeof res.courseId === 'string' ? res.courseId : courseId,
    required: res.required === true,
  }
}

export async function listResearchTeamApplications(): Promise<{
  applications: AdminResearchTeamApplication[]
}> {
  const raw = await httpGet<{ applications?: unknown }>('/research-team/applications')
  const applications = Array.isArray(raw.applications)
    ? raw.applications
        .map(normalizeAdminApplication)
        .filter((item): item is AdminResearchTeamApplication => item !== null)
    : []
  return { applications }
}

export async function getResearchTeamApplication(
  applicationId: string,
): Promise<AdminResearchTeamApplication> {
  const raw = await httpGet<unknown>(
    `/research-team/applications/${encodeURIComponent(applicationId)}`,
  )
  const application = normalizeAdminApplication(raw)
  if (!application) {
    throw new Error('Failed to load research team application: invalid response')
  }
  return application
}

export async function patchResearchTeamApplicationStatus(
  applicationId: string,
  status: ResearchTeamApplicationStatus,
): Promise<AdminResearchTeamApplication> {
  const raw = await httpPatch<unknown>(
    `/research-team/applications/${encodeURIComponent(applicationId)}`,
    { status },
  )
  const application = normalizeAdminApplication(raw)
  if (!application) {
    throw new Error('Failed to update research team application: invalid response')
  }
  return application
}

export async function allowResearchTeamReapply(
  applicationId: string,
): Promise<AdminResearchTeamApplication> {
  const raw = await httpPost<unknown>(
    `/research-team/applications/${encodeURIComponent(applicationId)}/allow-reapply`,
    {},
  )
  const application = normalizeAdminApplication(raw)
  if (!application) {
    throw new Error('Failed to allow research team reapply: invalid response')
  }
  return application
}
