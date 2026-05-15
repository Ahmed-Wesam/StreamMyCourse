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
    if (typeof j.message === 'string' && j.message.trim()) message = j.message.trim()
    if (typeof j.code === 'string' && j.code.trim()) code = j.code.trim()
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
 * True when progress tracking is unavailable because RDS is not configured.
 * The API returns 503 with code `progress_requires_rds`.
 */
export function isProgressRdsUnavailableError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.status === 503 && e.code === 'progress_requires_rds') return true
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

/** True when module deletion failed because the course must keep at least one module. */
export function isLastModuleDeleteError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'last_module_required' && e.status === 400) return true
  if (e.status === 400 && /last module/i.test(e.message)) return true
  return false
}

/** True when module deletion is blocked because the media cleanup queue is not configured. */
export function isMediaCleanupUnavailableError(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.code === 'media_cleanup_unavailable' && e.status === 503) return true
  if (e.status === 503 && /media cleanup/i.test(e.message)) return true
  return false
}

function requireApiBaseUrl(): string {
  const base = API_BASE_URL_RAW?.trim()
  if (!base) {
    // Unit tests exercise request shape (path, headers, body). They don't require a real API base URL.
    if (import.meta.env.MODE === 'test') return 'https://example.test'
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

export type CourseModule = {
  id: string
  title: string
  description: string
  order: number
  createdAt?: string
  updatedAt?: string
  /** Present when the viewer may see that a module quiz exists (enrolled + visibility rules). */
  moduleQuiz?: { available: boolean; servedCountN: number }
}

export type ModuleQuizOption = {
  key: string
  text: string
}

export type ModuleQuizQuestion = {
  id: string
  promptText: string
  optionsJson: ModuleQuizOption[]
}

/** Per-question scored row (submit 200 or latest submission breakdown). */
export type ModuleQuizResultQuestion = {
  id: string
  promptText: string
  selectedOptionKey: string
  correctOptionKey: string
  isCorrect: boolean
}

export type ModuleQuizLatestSubmission = {
  correctCount: number
  totalCount: number
  attemptNumber: number
  submittedAt?: string | null
  questions: ModuleQuizResultQuestion[]
}

export type ModuleQuizStartInProgress = {
  phase: 'in_progress'
  moduleQuizId: string
  moduleId: string
  servedCountN: number
  attemptId: string
  attemptNumber: number
  /** Display order; matches `questions[].id` order. */
  questionIds: string[]
  questions: ModuleQuizQuestion[]
}

export type ModuleQuizStartLatestResults = {
  phase: 'latest_results'
  moduleQuizId: string
  moduleId: string
  servedCountN: number
  latestSubmission: ModuleQuizLatestSubmission
}

export type ModuleQuizStartResponse = ModuleQuizStartInProgress | ModuleQuizStartLatestResults

export type ModuleQuizSubmitBody = {
  attemptId: string
  answers: Record<string, string>
}

export type ModuleQuizSubmitResponse = {
  attemptId: string
  attemptNumber: number
  correctCount: number
  totalCount: number
  questions: ModuleQuizResultQuestion[]
}

export type Lesson = {
  id: string
  title: string
  order: number
  moduleId: string
  /** Display order of the parent module within the course */
  moduleOrder: number
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
  /** When omitted the API attaches the lesson to the first module by order. */
  moduleId?: string
}

type CreateCourseModuleInput = {
  title: string
  description?: string
}

type Playback = {
  url: string
}

export type LessonProgressItem = {
  lessonId: string
  completed: boolean
  completedAt?: string
  lastPositionSec: number
}

export type CourseProgress = {
  courseId: string
  totalReadyLessons: number
  completedCount: number
  percentComplete: number
  lessons: LessonProgressItem[]
}

export type UpdateLessonProgressBody = {
  lastPositionSec: number
  /** Total lesson length in seconds (from `Lesson.duration` or `HTMLVideoElement.duration`); sent to the API as `duration`. */
  durationSec: number
  markComplete?: boolean
  markIncomplete?: boolean
}

export type UpdateProgressResponse = {
  ok: true
  lessonProgress?: LessonProgressItem
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

export async function listCourseModules(courseId: string): Promise<CourseModule[]> {
  return httpGet<CourseModule[]>(`/courses/${courseId}/modules`)
}

/** Start or resume a module quiz for the signed-in student (idempotent). Pass `{ retake: true }` for a new attempt after submit. */
export async function startModuleQuiz(
  courseId: string,
  moduleId: string,
  body: Record<string, unknown> = {},
): Promise<ModuleQuizStartResponse> {
  return httpPost<ModuleQuizStartResponse>(
    `/courses/${courseId}/modules/${moduleId}/quiz/start`,
    body,
  )
}

export async function submitModuleQuiz(
  courseId: string,
  moduleId: string,
  body: ModuleQuizSubmitBody,
): Promise<ModuleQuizSubmitResponse> {
  return httpPost<ModuleQuizSubmitResponse>(
    `/courses/${courseId}/modules/${moduleId}/quiz/submit`,
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

export async function createCourseModule(
  courseId: string,
  input: CreateCourseModuleInput,
): Promise<{ moduleId: string; order: number }> {
  const body: Record<string, string> = { title: input.title }
  if (input.description !== undefined) body.description = input.description
  return httpPost<{ moduleId: string; order: number }>(`/courses/${courseId}/modules`, body)
}

export async function deleteCourseModule(
  courseId: string,
  moduleId: string,
): Promise<{ moduleId: string; deleted: boolean }> {
  return httpDelete<{ moduleId: string; deleted: boolean }>(`/courses/${courseId}/modules/${moduleId}`)
}

export async function createLesson(
  courseId: string,
  input: CreateLessonInput,
): Promise<{ lessonId: string; moduleId: string; order: number }> {
  return httpPost<{ lessonId: string; moduleId: string; order: number }>(
    `/courses/${courseId}/lessons`,
    input,
  )
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

/** Get the viewer's progress for a course. */
export async function getCourseProgress(courseId: string): Promise<CourseProgress> {
  return httpGet<CourseProgress>(`/courses/${courseId}/progress`)
}

/** Update progress for a specific lesson (position, completion). */
export async function updateLessonProgress(
  courseId: string,
  lessonId: string,
  body: UpdateLessonProgressBody,
): Promise<UpdateProgressResponse> {
  const payload: Record<string, unknown> = {
    position: body.lastPositionSec,
    duration: body.durationSec,
  }
  if (body.markComplete) payload.markComplete = true
  if (body.markIncomplete) payload.markIncomplete = true
  return httpPut<UpdateProgressResponse>(`/courses/${courseId}/lessons/${lessonId}/progress`, payload)
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
