/**
 * Authenticated certificates API:
 * - Student: GET /me/certificates
 * - Teacher (owner/admin): GET /courses/{courseId}/certificates,
 *   POST /courses/{courseId}/certificates/{certificateId}/revoke
 */

import { httpGet, httpPost } from './client'

type CertificateStatus = 'valid' | 'revoked'

type MyCertificate = {
  id: string
  credentialId: string
  status: CertificateStatus
  studentName: string
  courseTitle: string
  /** Already-formatted issue label from the API (e.g. "September 2026"). */
  issueDate: string
  instructorName: string
  instructorTitle: string
  courseId: string
}

/** Course-scoped certificate row for instructors (owner/admin). */
export type CourseCertificate = {
  id: string
  credentialId: string
  status: CertificateStatus
  studentName: string
  courseTitle: string
  /** Already-formatted issue label from the API (e.g. "September 2026"). */
  issueDate: string
}

type CertificateInProgress = {
  courseId: string
  courseTitle: string
  passedCount: number
  totalCount: number
}

type CertificateProfileIncomplete = {
  courseId: string
  courseTitle: string
  requirementsMet: boolean
  message: string
  href: string
}

export type MeCertificatesResponse = {
  certificates: MyCertificate[]
  inProgress: CertificateInProgress[]
  profileIncomplete: CertificateProfileIncomplete[]
}

function normalizeStatus(value: unknown): CertificateStatus {
  return value === 'revoked' ? 'revoked' : 'valid'
}

function normalizeMineItem(row: unknown): MyCertificate | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const id = typeof record.id === 'string' ? record.id.trim() : ''
  const credentialId = typeof record.credentialId === 'string' ? record.credentialId.trim() : ''
  if (!id || !credentialId) return null

  return {
    id,
    credentialId,
    status: normalizeStatus(record.status),
    studentName: typeof record.studentName === 'string' ? record.studentName : '',
    courseTitle: typeof record.courseTitle === 'string' ? record.courseTitle : '',
    issueDate: typeof record.issueDate === 'string' ? record.issueDate : '',
    instructorName: typeof record.instructorName === 'string' ? record.instructorName : '',
    instructorTitle: typeof record.instructorTitle === 'string' ? record.instructorTitle : '',
    courseId: typeof record.courseId === 'string' ? record.courseId : '',
  }
}

function normalizeInProgress(row: unknown): CertificateInProgress | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const courseId = typeof record.courseId === 'string' ? record.courseId.trim() : ''
  const courseTitle = typeof record.courseTitle === 'string' ? record.courseTitle : ''
  if (!courseId) return null
  const passedCount = typeof record.passedCount === 'number' ? record.passedCount : 0
  const totalCount = typeof record.totalCount === 'number' ? record.totalCount : 0
  return { courseId, courseTitle, passedCount, totalCount }
}

function normalizeProfileIncomplete(row: unknown): CertificateProfileIncomplete | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const courseId = typeof record.courseId === 'string' ? record.courseId.trim() : ''
  if (!courseId) return null
  return {
    courseId,
    courseTitle: typeof record.courseTitle === 'string' ? record.courseTitle : '',
    requirementsMet: record.requirementsMet === true,
    message: typeof record.message === 'string' ? record.message : '',
    href: typeof record.href === 'string' ? record.href : '/account/profile',
  }
}

export async function listMyCertificates(): Promise<MeCertificatesResponse> {
  const raw = await httpGet<Record<string, unknown>>('/me/certificates')
  const certificates = Array.isArray(raw.certificates)
    ? raw.certificates.map(normalizeMineItem).filter((item): item is MyCertificate => item !== null)
    : []
  const inProgress = Array.isArray(raw.inProgress)
    ? raw.inProgress
        .map(normalizeInProgress)
        .filter((item): item is CertificateInProgress => item !== null)
    : []
  const profileIncomplete = Array.isArray(raw.profileIncomplete)
    ? raw.profileIncomplete
        .map(normalizeProfileIncomplete)
        .filter((item): item is CertificateProfileIncomplete => item !== null)
    : []
  return { certificates, inProgress, profileIncomplete }
}

function normalizeCourseItem(row: unknown): CourseCertificate | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const id = typeof record.id === 'string' ? record.id.trim() : ''
  const credentialId = typeof record.credentialId === 'string' ? record.credentialId.trim() : ''
  if (!id || !credentialId) return null

  return {
    id,
    credentialId,
    status: normalizeStatus(record.status),
    studentName: typeof record.studentName === 'string' ? record.studentName : '',
    courseTitle: typeof record.courseTitle === 'string' ? record.courseTitle : '',
    issueDate: typeof record.issueDate === 'string' ? record.issueDate : '',
  }
}

export async function listCourseCertificates(
  courseId: string,
): Promise<{ certificates: CourseCertificate[] }> {
  const c = encodeURIComponent(courseId)
  const raw = await httpGet<Record<string, unknown>>(`/courses/${c}/certificates`)
  const certificates = Array.isArray(raw.certificates)
    ? raw.certificates
        .map(normalizeCourseItem)
        .filter((item): item is CourseCertificate => item !== null)
    : []
  return { certificates }
}

export async function revokeCourseCertificate(
  courseId: string,
  certificateId: string,
): Promise<{ id: string; credentialId: string; status: CertificateStatus }> {
  const c = encodeURIComponent(courseId)
  const id = encodeURIComponent(certificateId)
  const raw = await httpPost<Record<string, unknown>>(
    `/courses/${c}/certificates/${id}/revoke`,
    {},
  )
  const responseId = typeof raw.id === 'string' ? raw.id.trim() : certificateId
  const credentialId = typeof raw.credentialId === 'string' ? raw.credentialId.trim() : ''
  return {
    id: responseId,
    credentialId,
    status: normalizeStatus(raw.status),
  }
}
