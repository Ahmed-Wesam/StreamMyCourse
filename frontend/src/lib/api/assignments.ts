import { failedResponseError, httpGet, httpPatch, httpPost } from './client'
import type {
  Assignment,
  AssignmentImageUploadResponse,
  AssignmentPresignedUrlResponse,
  AssignmentSubmissionFile,
  AssignmentSubmissionListItem,
  CompleteAssignmentSubmissionFileResponse,
  CreateAssignmentBody,
  CreateAssignmentSubmissionFileResponse,
  CreateAssignmentSubmissionResponse,
  GradeAssignmentBody,
  GradeAssignmentSubmissionResponse,
  PatchAssignmentBody,
  SubmitAssignmentSubmissionResponse,
} from './types'

type ListAssignmentsResponse = { assignments: Assignment[] }
type AssignmentResponse = { assignment: Assignment }
type ListSubmissionsResponse = { submissions: AssignmentSubmissionListItem[] }
type SubmissionResponse = { submission: CreateAssignmentSubmissionResponse }
type CompleteFileResponse = { file: { id: string; status: 'ready' } }

type ApiSubmissionRow = {
  id: string
  status: AssignmentSubmissionListItem['status']
  note?: string
  files?: AssignmentSubmissionFile[]
  grade?: {
    scorePercent: number
    passed: boolean
    feedback?: string
  }
}

function normalizeSubmissionRow(row: ApiSubmissionRow): AssignmentSubmissionListItem {
  return {
    id: row.id,
    status: row.status,
    note: row.note,
    scorePercent: row.grade?.scorePercent,
    passed: row.grade?.passed,
    feedback: row.grade?.feedback,
    files: row.files,
  }
}

export async function listCourseAssignments(
  courseId: string,
  opts?: { moduleId?: string },
): Promise<Assignment[]> {
  const qs = opts?.moduleId ? `?moduleId=${encodeURIComponent(opts.moduleId)}` : ''
  const res = await httpGet<ListAssignmentsResponse>(`/courses/${courseId}/assignments${qs}`)
  const items = Array.isArray(res?.assignments) ? res.assignments : []
  if (opts?.moduleId) {
    return items.filter((a) => a.moduleId === opts.moduleId)
  }
  return items
}

export async function getAssignment(courseId: string, assignmentId: string): Promise<Assignment> {
  const res = await httpGet<AssignmentResponse>(`/courses/${courseId}/assignments/${assignmentId}`)
  return res.assignment
}

export async function createAssignment(
  courseId: string,
  body: CreateAssignmentBody,
): Promise<Assignment> {
  const res = await httpPost<AssignmentResponse>(`/courses/${courseId}/assignments`, body)
  return res.assignment
}

export async function patchAssignment(
  courseId: string,
  assignmentId: string,
  body: PatchAssignmentBody,
): Promise<Assignment> {
  const res = await httpPatch<AssignmentResponse>(
    `/courses/${courseId}/assignments/${assignmentId}`,
    body,
  )
  return res.assignment
}

export async function createAssignmentImageUpload(
  courseId: string,
  assignmentId: string,
  body: { slot: 'instructions' | 'rubric'; contentType: string; byteSize: number },
): Promise<AssignmentImageUploadResponse> {
  return httpPost<AssignmentImageUploadResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/images`,
    body,
  )
}

export async function completeAssignmentImageUpload(
  courseId: string,
  assignmentId: string,
  slot: 'instructions' | 'rubric',
): Promise<{ slot: string; status: 'ready' }> {
  return httpPost<{ slot: string; status: 'ready' }>(
    `/courses/${courseId}/assignments/${assignmentId}/images/${slot}/complete`,
    {},
  )
}

export async function getAssignmentImageUrl(
  courseId: string,
  assignmentId: string,
  slot: 'instructions' | 'rubric',
): Promise<AssignmentPresignedUrlResponse> {
  return httpGet<AssignmentPresignedUrlResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/images/${slot}/url`,
  )
}

export async function createAssignmentSubmission(
  courseId: string,
  assignmentId: string,
): Promise<CreateAssignmentSubmissionResponse> {
  const res = await httpPost<SubmissionResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions`,
    {},
  )
  return res.submission
}

export async function createAssignmentSubmissionFile(
  courseId: string,
  assignmentId: string,
  submissionId: string,
  body: { title: string; fileType: string; byteSize: number },
): Promise<CreateAssignmentSubmissionFileResponse> {
  return httpPost<CreateAssignmentSubmissionFileResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions/${submissionId}/files`,
    body,
  )
}

export async function completeAssignmentSubmissionFile(
  courseId: string,
  assignmentId: string,
  submissionId: string,
  fileId: string,
): Promise<CompleteAssignmentSubmissionFileResponse> {
  const res = await httpPost<CompleteFileResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions/${submissionId}/files/${fileId}/complete`,
    {},
  )
  return { fileId: res.file.id, status: res.file.status }
}

export async function getAssignmentSubmissionFileUrl(
  courseId: string,
  assignmentId: string,
  submissionId: string,
  fileId: string,
): Promise<AssignmentPresignedUrlResponse> {
  return httpGet<AssignmentPresignedUrlResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions/${submissionId}/files/${fileId}/url`,
  )
}

export async function submitAssignmentSubmission(
  courseId: string,
  assignmentId: string,
  submissionId: string,
  body?: { note?: string },
): Promise<SubmitAssignmentSubmissionResponse> {
  return httpPost<SubmitAssignmentSubmissionResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions/${submissionId}/submit`,
    body ?? {},
  )
}

export async function listAssignmentSubmissions(
  courseId: string,
  assignmentId: string,
): Promise<AssignmentSubmissionListItem[]> {
  const res = await httpGet<ListSubmissionsResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions`,
  )
  const rows = Array.isArray(res?.submissions) ? res.submissions : []
  return rows.map((row) => normalizeSubmissionRow(row as ApiSubmissionRow))
}

export async function gradeAssignmentSubmission(
  courseId: string,
  assignmentId: string,
  submissionId: string,
  body: GradeAssignmentBody,
): Promise<GradeAssignmentSubmissionResponse> {
  return httpPost<GradeAssignmentSubmissionResponse>(
    `/courses/${courseId}/assignments/${assignmentId}/submissions/${submissionId}/grade`,
    body,
  )
}

/** PUT bytes to a presigned upload URL (assignment image or submission file). */
export async function putAssignmentUpload(
  uploadUrl: string,
  file: Blob,
  contentType: string,
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
}
