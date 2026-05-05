import { fetchAuthSession } from 'aws-amplify/auth'

import { isAuthConfigured } from './auth'

const API_BASE_URL_RAW = import.meta.env.VITE_API_BASE_URL as string | undefined

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

async function failedResponseError(res: Response): Promise<ApiError> {
  let message = `Request failed: ${res.status}`
  let code: string | undefined
  try {
    const j = (await res.json()) as { message?: string; code?: string }
    if (typeof j.message === 'string' && j.message.trim()) message = j.message
    if (typeof j.code === 'string' && j.code.trim()) code = j.code
  } catch {
    /* ignore non-JSON */
  }
  return new ApiError(message, res.status, code)
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

/**
 * True when playback was denied because the caller is not authenticated
 * (missing or rejected token at the gateway, or Lambda `unauthorized`).
 */
export function isPlaybackAuthRequiredError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.status === 401) return true
  if (e.code === 'unauthorized') return true
  return false
}

/** Progress API unavailable: Cognito not configured on API (503 auth_not_configured). */
export function isProgressAuthNotConfiguredError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 503 && e.code === 'auth_not_configured'
}

/** Progress requires RDS but catalog is on DynamoDB-only (503 progress_requires_rds). */
export function isProgressRdsUnavailableError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 503 && e.code === 'progress_requires_rds'
}

function requireApiBaseUrl(): string {
  const base = API_BASE_URL_RAW?.trim()
  if (!base) {
    throw new Error(
      'VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env and set the API base URL.',
    )
  }
  return base
}

function bearerFromSession(session: Awaited<ReturnType<typeof fetchAuthSession>>): string | undefined {
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
      session = await fetchAuthSession({ forceRefresh: true })
      token = bearerFromSession(session)
    }
    if (!token) return {}
    return { Authorization: `Bearer ${token}` }
  } catch {
    return {}
  }
}

async function mergeHeaders(base?: HeadersInit): Promise<Headers> {
  const h = new Headers(base)
  const auth = await authHeader()
  if (auth.Authorization) {
    h.set('Authorization', auth.Authorization)
  }
  return h
}

/** True when Cognito is configured and the user has an ID token (signed in). */
export async function hasSignedInIdToken(): Promise<boolean> {
  if (!isAuthConfigured()) return false
  try {
    const session = await fetchAuthSession()
    return Boolean(bearerFromSession(session))
  } catch {
    return false
  }
}

export type Course = {
  id: string
  title: string
  description: string
  status: 'DRAFT' | 'PUBLISHED'
  createdAt?: string
  updatedAt?: string
  /** Presigned GET URL when the course has a thumbnail; omit if none. */
  thumbnailUrl?: string
  /** True when the viewer is enrolled; false for anonymous or not-yet-enrolled on a published course. */
  enrolled?: boolean
}

export type Lesson = {
  id: string
  title: string
  order: number
  videoStatus: 'pending' | 'ready'
  duration?: number
  /** Presigned GET when a lesson thumbnail exists. */
  thumbnailUrl?: string
}

export type UserProfile = {
  userId: string
  email: string
  role: string
  cognitoSub: string
  createdAt: string
  updatedAt: string
}

type CreateCourseInput = {
  title: string
  description: string
}

type CreateLessonInput = {
  title: string
}

type Playback = {
  url: string
}

export type CourseProgressLesson = {
  lessonId: string
  completed: boolean
  completedAt?: string | null
  lastPositionSec: number
}

export type CourseProgress = {
  courseId: string
  totalReadyLessons: number
  completedCount: number
  percentComplete: number
  lessons: CourseProgressLesson[]
}

export type LessonProgressUpdateBody = {
  lastPositionSec?: number
  markComplete?: boolean
  markIncomplete?: boolean
}

export type LessonProgressUpdateResult = {
  ok: boolean
  throttled?: boolean
}

/** Presigned PUT target: lesson video, course thumbnail, or lesson thumbnail image. */
type UploadUrlTarget =
  | { courseId: string; lessonId: string; uploadKind?: 'lesson' }
  | { courseId: string; uploadKind: 'thumbnail' }
  | { courseId: string; lessonId: string; uploadKind: 'lessonThumbnail' }

async function httpGet<T>(path: string): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ Accept: 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: 'no-store', headers })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
  return (await res.json()) as T
}

async function httpPost<T>(path: string, body: unknown): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    cache: 'no-store',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
  return (await res.json()) as T
}

async function httpPut<T>(path: string, body?: unknown): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    cache: 'no-store',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
  return (await res.json()) as T
}

async function httpDelete<T>(path: string): Promise<T> {
  const API_BASE_URL = requireApiBaseUrl()
  const headers = await mergeHeaders({ Accept: 'application/json' })
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    cache: 'no-store',
    headers,
  })
  if (!res.ok) {
    throw await failedResponseError(res)
  }
  return (await res.json()) as T
}

export async function listCourses(): Promise<Course[]> {
  return httpGet<Course[]>('/courses')
}

/** Instructor dashboard: all courses the signed-in teacher owns (draft + published). */
export async function listInstructorCourses(): Promise<Course[]> {
  return httpGet<Course[]>('/courses/mine')
}

export async function getCourse(courseId: string): Promise<Course> {
  return httpGet<Course>(`/courses/${courseId}`)
}

/** Self-service enrollment on a published course (requires Cognito when API enforces auth). */
export async function enrollInCourse(courseId: string): Promise<{ courseId: string; enrolled: boolean }> {
  return httpPost<{ courseId: string; enrolled: boolean }>(`/courses/${courseId}/enroll`, {})
}

export async function listLessons(courseId: string): Promise<Lesson[]> {
  return httpGet<Lesson[]>(`/courses/${courseId}/lessons`)
}

export async function getCourseProgress(courseId: string): Promise<CourseProgress> {
  return httpGet<CourseProgress>(`/courses/${courseId}/progress`)
}

export async function updateLessonProgress(
  courseId: string,
  lessonId: string,
  body: LessonProgressUpdateBody,
): Promise<LessonProgressUpdateResult> {
  return httpPut<LessonProgressUpdateResult>(
    `/courses/${courseId}/lessons/${lessonId}/progress`,
    body,
  )
}

export async function getPlaybackUrl(courseId: string, lessonId: string): Promise<Playback> {
  return httpGet<Playback>(`/playback/${courseId}/${lessonId}`)
}

export async function fetchMe(): Promise<UserProfile> {
  return httpGet<UserProfile>('/users/me')
}

export async function createCourse(input: CreateCourseInput): Promise<{ id: string; status: string }> {
  return httpPost<{ id: string; status: string }>('/courses', input)
}

export async function updateCourse(
  courseId: string,
  input: CreateCourseInput,
): Promise<{ id: string; updated: boolean }> {
  return httpPut<{ id: string; updated: boolean }>(`/courses/${courseId}`, input)
}

export async function deleteCourse(courseId: string): Promise<{ id: string; deleted: boolean }> {
  return httpDelete<{ id: string; deleted: boolean }>(`/courses/${courseId}`)
}

export async function publishCourse(courseId: string): Promise<{ id: string; status: string }> {
  return httpPut<{ id: string; status: string }>(`/courses/${courseId}/publish`)
}

export async function createLesson(
  courseId: string,
  input: CreateLessonInput,
): Promise<{ lessonId: string; order: number }> {
  return httpPost<{ lessonId: string; order: number }>(`/courses/${courseId}/lessons`, input)
}

export async function deleteLesson(
  courseId: string,
  lessonId: string,
): Promise<{ lessonId: string; deleted: boolean }> {
  return httpDelete<{ lessonId: string; deleted: boolean }>(`/courses/${courseId}/lessons/${lessonId}`)
}

export async function markLessonVideoReady(
  courseId: string,
  lessonId: string,
  options?: { thumbnailKey?: string },
): Promise<{ lessonId: string; videoStatus: string }> {
  const body =
    options?.thumbnailKey !== undefined && options.thumbnailKey !== ''
      ? { thumbnailKey: options.thumbnailKey }
      : undefined
  return httpPut<{ lessonId: string; videoStatus: string }>(
    `/courses/${courseId}/lessons/${lessonId}/video-ready`,
    body,
  )
}

/** After PUT upload to S3 using `thumbnailKey` from `getUploadUrl`, persist the course thumbnail. */
export async function markCourseThumbnailReady(
  courseId: string,
  thumbnailKey: string,
): Promise<{ id: string; thumbnailReady: boolean }> {
  return httpPut<{ id: string; thumbnailReady: boolean }>(`/courses/${courseId}/thumbnail-ready`, {
    thumbnailKey,
  })
}

/**
 * Presigned upload: lesson video, course thumbnail (`uploadKind: 'thumbnail'`),
 * or lesson thumbnail JPEG (`uploadKind: 'lessonThumbnail'` + `lessonId`).
 */
export async function getUploadUrl(
  filename: string,
  contentType: string,
  target: UploadUrlTarget,
): Promise<{ uploadUrl: string; videoKey?: string; thumbnailKey?: string }> {
  const API_BASE_URL = requireApiBaseUrl()
  const body: Record<string, string> = {
    filename,
    contentType,
    courseId: target.courseId,
  }
  if ('uploadKind' in target && target.uploadKind === 'thumbnail') {
    body.uploadKind = 'thumbnail'
  } else if ('uploadKind' in target && target.uploadKind === 'lessonThumbnail') {
    body.uploadKind = 'lessonThumbnail'
    body.lessonId = target.lessonId
  } else if ('lessonId' in target) {
    body.lessonId = target.lessonId
  }

  const headers = await mergeHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}/upload-url`, {
    method: 'POST',
    cache: 'no-store',
    headers,
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    throw await failedResponseError(res)
  }

  return res.json() as Promise<{ uploadUrl: string; videoKey?: string; thumbnailKey?: string }>
}
