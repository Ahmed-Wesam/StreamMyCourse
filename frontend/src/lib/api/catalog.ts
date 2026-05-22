import { failedResponseError, httpDelete, httpGet, httpPost, httpPut, mergeHeaders, requireApiBaseUrl } from './client'
import type {
  Course,
  CourseModule,
  CourseProgress,
  Lesson,
  UpdateLessonProgressBody,
  UpdateProgressResponse,
} from './types'

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

/** Presigned PUT target: lesson video, course thumbnail, or lesson thumbnail image. */
type UploadUrlTarget =
  | { courseId: string; lessonId: string; uploadKind?: 'lesson' }
  | { courseId: string; uploadKind: 'thumbnail' }
  | { courseId: string; lessonId: string; uploadKind: 'lessonThumbnail' }

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

/**
 * Self-service enrollment on a published course (requires Cognito when API enforces auth).
 * @deprecated Subscription access replaces per-course enroll for students; kept for API client tests.
 */
export async function enrollInCourse(courseId: string): Promise<{ courseId: string; enrolled: boolean }> {
  return httpPost<{ courseId: string; enrolled: boolean }>(`/courses/${courseId}/enroll`, {})
}

export async function listLessons(courseId: string): Promise<Lesson[]> {
  return httpGet<Lesson[]>(`/courses/${courseId}/lessons`)
}

export async function listCourseModules(courseId: string): Promise<CourseModule[]> {
  return httpGet<CourseModule[]>(`/courses/${courseId}/modules`)
}

export async function getPlaybackUrl(courseId: string, lessonId: string): Promise<Playback> {
  return httpGet<Playback>(`/playback/${courseId}/${lessonId}`)
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
