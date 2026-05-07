/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

vi.mock('./auth', () => ({
  isAuthConfigured: () => true,
}))

import {
  ApiError,
  createCourse,
  createCourseModule,
  createLesson,
  deleteCourse,
  deleteCourseModule,
  deleteLesson,
  enrollInCourse,
  fetchMe,
  getCourse,
  getCourseProgress,
  getPlaybackUrl,
  getUploadUrl,
  isEnrollmentRequiredError,
  isLastModuleDeleteError,
  isMediaCleanupUnavailableError,
  isPlaybackAuthRequiredError,
  isProgressAuthNotConfiguredError,
  isProgressRdsUnavailableError,
  listCourseModules,
  listCourses,
  listInstructorCourses,
  listLessons,
  markCourseThumbnailReady,
  markLessonVideoReady,
  publishCourse,
  updateCourse,
  updateLessonProgress,
} from './api'

describe('catalog GET without signed-in session', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.toString()
        if (url.includes('/modules') && init?.method === 'POST') {
          return new Response(JSON.stringify({ moduleId: 'm1', order: 0 }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        }
        if (url.includes('/modules') && init?.method === 'DELETE') {
          return new Response(JSON.stringify({ moduleId: 'm1', deleted: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        }
        const body = url.includes('/lessons')
          ? []
          : url.includes('/modules')
            ? [{ id: 'm1', title: 'Intro', description: '', order: 0 }]
            : { id: 'x', title: 'T', description: 'D', status: 'PUBLISHED' }
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('getCourse does not send Authorization when no id token', async () => {
    await getCourse('course-1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const h = new Headers(init?.headers as HeadersInit)
    expect(h.has('Authorization')).toBe(false)
  })

  it('listLessons does not send Authorization when no id token', async () => {
    await listLessons('course-1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const h = new Headers(init?.headers as HeadersInit)
    expect(h.has('Authorization')).toBe(false)
  })

  it('getCourse sends Bearer when id token is present', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: 'jwt-token-abc' },
    })
    await getCourse('course-1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const h = new Headers(init?.headers as HeadersInit)
    expect(h.get('Authorization')).toBe('Bearer jwt-token-abc')
  })

  it('listLessons sends Bearer when id token is present', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: 'jwt-token-xyz' },
    })
    await listLessons('course-1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const h = new Headers(init?.headers as HeadersInit)
    expect(h.get('Authorization')).toBe('Bearer jwt-token-xyz')
  })

  it('listCourseModules sends Bearer when id token is present', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: 'jwt-token-modules' },
    })
    await listCourseModules('course-1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const h = new Headers(init?.headers as HeadersInit)
    expect(h.get('Authorization')).toBe('Bearer jwt-token-modules')
  })

  it('listCourseModules calls /courses/{id}/modules', async () => {
    await listCourseModules('course-1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/course-1/modules')
  })

  it('createCourseModule posts to /courses/{id}/modules with title only when description omitted', async () => {
    await createCourseModule('course-1', { title: 'Intro' })
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/course-1/modules')
    expect(init?.method).toBe('POST')
    const sent = JSON.parse((init?.body as string) ?? '{}') as Record<string, unknown>
    expect(sent).toEqual({ title: 'Intro' })
  })

  it('createCourseModule includes description when provided', async () => {
    await createCourseModule('course-1', { title: 'Intro', description: 'desc' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const sent = JSON.parse((init?.body as string) ?? '{}') as Record<string, unknown>
    expect(sent).toEqual({ title: 'Intro', description: 'desc' })
  })

  it('deleteCourseModule deletes /courses/{id}/modules/{moduleId}', async () => {
    await deleteCourseModule('course-1', 'm1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/course-1/modules/m1')
    expect(init?.method).toBe('DELETE')
  })
})

describe('isEnrollmentRequiredError', () => {
  it('matches enrollment_required code', () => {
    expect(isEnrollmentRequiredError(new ApiError('x', 403, 'enrollment_required'))).toBe(true)
  })

  it('matches 403 with enrollment wording when code omitted', () => {
    expect(isEnrollmentRequiredError(new ApiError('Enrollment required to view', 403))).toBe(true)
    expect(isEnrollmentRequiredError(new ApiError('Forbidden', 403))).toBe(false)
  })

  it('is false for non-ApiError', () => {
    expect(isEnrollmentRequiredError(new Error('enrollment'))).toBe(false)
  })
})

describe('isPlaybackAuthRequiredError', () => {
  it('is true for 401 ApiError', () => {
    expect(isPlaybackAuthRequiredError(new ApiError('nope', 403))).toBe(false)
    expect(isPlaybackAuthRequiredError(new ApiError('auth', 401, 'unauthorized'))).toBe(true)
  })

  it('is true when code is unauthorized even if status is not 401', () => {
    expect(isPlaybackAuthRequiredError(new ApiError('auth', 403, 'unauthorized'))).toBe(true)
  })

  it('is false for non-ApiError', () => {
    expect(isPlaybackAuthRequiredError(new Error('fail'))).toBe(false)
  })
})

describe('module error helpers', () => {
  it('isLastModuleDeleteError matches 400 + last_module_required code before message', () => {
    expect(isLastModuleDeleteError(new ApiError('Anything', 400, 'last_module_required'))).toBe(true)
    expect(isLastModuleDeleteError(new ApiError('Cannot delete the last module in a course', 400))).toBe(true)
    expect(isLastModuleDeleteError(new ApiError('Cannot delete module', 400))).toBe(false)
    expect(isLastModuleDeleteError(new ApiError('Cannot delete the last module in a course', 500))).toBe(false)
    expect(isLastModuleDeleteError(new Error('Cannot delete the last module in a course'))).toBe(false)
  })

  it('isMediaCleanupUnavailableError matches 503 + media_cleanup_unavailable code before message', () => {
    expect(isMediaCleanupUnavailableError(new ApiError('Anything', 503, 'media_cleanup_unavailable'))).toBe(true)
    expect(isMediaCleanupUnavailableError(new ApiError('Media cleanup queue is not configured', 503))).toBe(true)
    expect(isMediaCleanupUnavailableError(new ApiError('progress requires rds', 503, 'progress_requires_rds'))).toBe(
      false,
    )
    expect(isMediaCleanupUnavailableError(new ApiError('Progress requires RDS', 503, 'progress_requires_rds'))).toBe(
      false,
    )
    expect(isMediaCleanupUnavailableError(new ApiError('Media cleanup queue is not configured', 500))).toBe(false)
    expect(isMediaCleanupUnavailableError(new Error('Media cleanup queue is not configured'))).toBe(false)
  })
})

describe('getCourseProgress', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(
          JSON.stringify({
            courseId: 'course-1',
            totalReadyLessons: 3,
            completedCount: 1,
            percentComplete: 33,
            lessons: [
              { lessonId: 'l1', completed: true, lastPositionSec: 120, completedAt: '2024-01-01T00:00:00Z' },
              { lessonId: 'l2', completed: false, lastPositionSec: 30 },
              { lessonId: 'l3', completed: false, lastPositionSec: 0 },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls correct endpoint /courses/{id}/progress', async () => {
    await getCourseProgress('course-1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/courses/course-1/progress')
  })
})

describe('updateLessonProgress', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(
          JSON.stringify({ ok: true, lessonProgress: { lessonId: 'l1', completed: true, lastPositionSec: 100 } }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls correct endpoint with PUT and maps body to position/duration', async () => {
    await updateLessonProgress('course-1', 'lesson-1', {
      lastPositionSec: 100,
      durationSec: 600,
      markComplete: true,
    })
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/courses/course-1/lessons/lesson-1/progress')
    expect(init?.method).toBe('PUT')
    const sent = JSON.parse((init?.body as string) ?? '{}') as Record<string, unknown>
    expect(sent).toEqual({ position: 100, duration: 600, markComplete: true })
  })

  it('includes markIncomplete when requested', async () => {
    await updateLessonProgress('course-1', 'lesson-1', {
      lastPositionSec: 0,
      durationSec: 120,
      markIncomplete: true,
    })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const sent = JSON.parse((init?.body as string) ?? '{}') as Record<string, unknown>
    expect(sent).toEqual({ position: 0, duration: 120, markIncomplete: true })
  })
})

describe('isProgressRdsUnavailableError', () => {
  it('returns true for 503 with code progress_requires_rds', () => {
    expect(isProgressRdsUnavailableError(new ApiError('RDS unavailable', 503, 'progress_requires_rds'))).toBe(true)
  })

  it('returns false for other codes', () => {
    expect(isProgressRdsUnavailableError(new ApiError('Other error', 503, 'other_code'))).toBe(false)
    expect(isProgressRdsUnavailableError(new ApiError('No code', 503))).toBe(false)
  })

  it('returns false for non-503 errors even with correct code', () => {
    expect(isProgressRdsUnavailableError(new ApiError('Not 503', 500, 'progress_requires_rds'))).toBe(false)
  })

  it('returns false for non-ApiError', () => {
    expect(isProgressRdsUnavailableError(new Error('fail'))).toBe(false)
  })
})

describe('isProgressAuthNotConfiguredError', () => {
  it('returns true for 503 with code auth_not_configured', () => {
    expect(isProgressAuthNotConfiguredError(new ApiError('Auth not configured', 503, 'auth_not_configured'))).toBe(
      true,
    )
  })

  it('returns false for other codes', () => {
    expect(isProgressAuthNotConfiguredError(new ApiError('Other error', 503, 'other_code'))).toBe(false)
    expect(isProgressAuthNotConfiguredError(new ApiError('No code', 503))).toBe(false)
  })

  it('returns false for non-503 errors even with correct code', () => {
    expect(isProgressAuthNotConfiguredError(new ApiError('Not 503', 500, 'auth_not_configured'))).toBe(false)
  })

  it('returns false for non-ApiError', () => {
    expect(isProgressAuthNotConfiguredError(new Error('fail'))).toBe(false)
  })
})

describe('enrollInCourse', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(JSON.stringify({ courseId: 'c1', enrolled: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('POSTs to /courses/{id}/enroll', async () => {
    await enrollInCourse('course-99')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/course-99/enroll')
    expect(init?.method).toBe('POST')
  })
})

describe('getUploadUrl', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input, init) => {
        const body = JSON.parse((init?.body as string) ?? '{}') as Record<string, string>
        return new Response(
          JSON.stringify({
            uploadUrl: 'https://s3.example/put',
            videoKey: body.lessonId ? 'vk' : undefined,
            thumbnailKey: body.uploadKind === 'lessonThumbnail' ? 'tk' : undefined,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('posts lesson video shape with lessonId', async () => {
    await getUploadUrl('a.mp4', 'video/mp4', { courseId: 'c1', lessonId: 'l1' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse((init?.body as string) ?? '{}') as Record<string, string>
    expect(body).toMatchObject({
      filename: 'a.mp4',
      contentType: 'video/mp4',
      courseId: 'c1',
      lessonId: 'l1',
    })
    expect(body.uploadKind).toBeUndefined()
  })

  it('posts course thumbnail shape', async () => {
    await getUploadUrl('t.jpg', 'image/jpeg', { courseId: 'c1', uploadKind: 'thumbnail' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse((init?.body as string) ?? '{}') as Record<string, string>
    expect(body.uploadKind).toBe('thumbnail')
    expect(body.lessonId).toBeUndefined()
  })

  it('posts lesson thumbnail shape', async () => {
    await getUploadUrl('thumb.jpg', 'image/jpeg', {
      courseId: 'c1',
      lessonId: 'l2',
      uploadKind: 'lessonThumbnail',
    })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse((init?.body as string) ?? '{}') as Record<string, string>
    expect(body.uploadKind).toBe('lessonThumbnail')
    expect(body.lessonId).toBe('l2')
  })
})

describe('markLessonVideoReady', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(JSON.stringify({ lessonId: 'l1', videoStatus: 'ready' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('PUTs without JSON body when no thumbnailKey', async () => {
    await markLessonVideoReady('c1', 'l1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(init?.method)).toBe('PUT')
    expect(init?.body).toBeUndefined()
  })

  it('PUTs thumbnailKey in body when provided', async () => {
    await markLessonVideoReady('c1', 'l1', { thumbnailKey: 'k-thumb' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ thumbnailKey: 'k-thumb' })
  })

  it('omits body when thumbnailKey is empty string', async () => {
    await markLessonVideoReady('c1', 'l1', { thumbnailKey: '' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(init?.body).toBeUndefined()
  })
})

describe('failedResponseError via non-JSON body', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('not json', { status: 502, statusText: 'Bad Gateway' })),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('getCourse throws ApiError with status text when body is not JSON', async () => {
    await expect(getCourse('x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 502,
      message: 'Request failed: 502',
    })
  })
})

describe('listCourses', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify([{ id: 'c1', title: 'A', description: '', status: 'PUBLISHED' }]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('GETs /courses', async () => {
    const rows = await listCourses()
    expect(rows).toHaveLength(1)
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toMatch(/\/courses$/)
  })
})

describe('listInstructorCourses', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify([{ id: 'm1', title: 'Draft', description: '', status: 'DRAFT' }]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('GETs /courses/mine', async () => {
    await listInstructorCourses()
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/mine')
  })
})

describe('createCourse updateCourse deleteCourse publishCourse', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input, init) => {
        const method = init?.method ?? 'GET'
        const body = init?.body ? JSON.parse(init.body as string) : {}
        if (method === 'POST')
          return new Response(JSON.stringify({ id: 'new', status: 'DRAFT' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        if (method === 'PUT' && String(_input).includes('/publish'))
          return new Response(JSON.stringify({ id: 'c1', status: 'PUBLISHED' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        if (method === 'PUT')
          return new Response(JSON.stringify({ id: body.title ? 'c1' : 'c1', updated: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        if (method === 'DELETE')
          return new Response(JSON.stringify({ id: 'c1', deleted: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        return new Response('{}', { status: 200 })
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('createCourse POSTs /courses with body', async () => {
    await createCourse({ title: 'T', description: 'D' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toMatch(/\/courses$/)
    expect(init?.method).toBe('POST')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ title: 'T', description: 'D' })
  })
  it('updateCourse PUTs /courses/{id}', async () => {
    await updateCourse('c9', { title: 'T2', description: 'D2' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/c9')
    expect(init?.method).toBe('PUT')
  })
  it('deleteCourse DELETEs /courses/{id}', async () => {
    await deleteCourse('c9')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/c9')
    expect(init?.method).toBe('DELETE')
  })
  it('publishCourse PUTs /courses/{id}/publish', async () => {
    await publishCourse('c9')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/c9/publish')
    expect(init?.method).toBe('PUT')
  })
})

describe('getPlaybackUrl fetchMe deleteLesson markCourseThumbnailReady', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input, init) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        if (url.includes('/playback/'))
          return new Response(JSON.stringify({ url: 'https://cdn.example/video.m3u8' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        if (url.includes('/users/me'))
          return new Response(
            JSON.stringify({
              userId: 'u1',
              email: 'e@e.com',
              role: 'student',
              cognitoSub: 's',
              createdAt: '',
              updatedAt: '',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        if (method === 'DELETE' && url.includes('/lessons/'))
          return new Response(JSON.stringify({ lessonId: 'l1', deleted: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        if (method === 'PUT' && url.includes('/thumbnail-ready'))
          return new Response(JSON.stringify({ id: 'c1', thumbnailReady: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        return new Response('{}', { status: 200 })
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('getPlaybackUrl GETs /playback/{courseId}/{lessonId}', async () => {
    const p = await getPlaybackUrl('c1', 'l1')
    expect(p.url).toContain('m3u8')
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/playback/c1/l1')
  })
  it('fetchMe GETs /users/me', async () => {
    const me = await fetchMe()
    expect(me.email).toBe('e@e.com')
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/users/me')
  })
  it('deleteLesson DELETEs lesson path', async () => {
    await deleteLesson('c1', 'l9')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/c1/lessons/l9')
    expect(init?.method).toBe('DELETE')
  })
  it('markCourseThumbnailReady PUTs thumbnailKey', async () => {
    await markCourseThumbnailReady('c1', 'key-abc')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/courses/c1/thumbnail-ready')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ thumbnailKey: 'key-abc' })
  })
})

describe('createLesson', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ lessonId: 'l1', moduleId: 'm1', order: 0 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('POSTs lesson with optional moduleId', async () => {
    await createLesson('c1', { title: 'L', moduleId: 'm2' })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ title: 'L', moduleId: 'm2' })
  })
})

describe('fetchAuthSession forceRefresh when first session has no token', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ id: 'x', title: 'T', description: 'D', status: 'PUBLISHED' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock
      .mockResolvedValueOnce({ tokens: { idToken: undefined } })
      .mockResolvedValueOnce({ tokens: { idToken: 'refreshed-jwt' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('calls fetchAuthSession with forceRefresh then sends Bearer', async () => {
    await getCourse('c1')
    expect(fetchAuthSessionMock).toHaveBeenCalledTimes(2)
    expect(fetchAuthSessionMock.mock.calls[1][0]).toEqual({ forceRefresh: true })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers as HeadersInit).get('Authorization')).toBe('Bearer refreshed-jwt')
  })
})

describe('bearerFromSession edge cases', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ id: 'x', title: 'T', description: 'D', status: 'PUBLISHED' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('does not send Authorization when id token string is only whitespace', async () => {
    fetchAuthSessionMock
      .mockResolvedValueOnce({ tokens: { idToken: '  \t  ' } })
      .mockResolvedValueOnce({ tokens: { idToken: '   ' } })
    await getCourse('c1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers as HeadersInit).has('Authorization')).toBe(false)
  })
  it('sends Bearer when id token is non-string with usable toString', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { toString: () => '  embedded  ' } },
    })
    await getCourse('c1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers as HeadersInit).get('Authorization')).toBe('Bearer embedded')
  })
  it('does not send Authorization when toString yields object sentinel', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { toString: () => '[object Object]' } },
    })
    await getCourse('c1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers as HeadersInit).has('Authorization')).toBe(false)
  })
})

describe('authHeader swallows fetchAuthSession errors', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ id: 'x', title: 'T', description: 'D', status: 'PUBLISHED' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockRejectedValue(new Error('session offline'))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('issues request without Authorization header', async () => {
    await getCourse('c1')
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers as HeadersInit).has('Authorization')).toBe(false)
  })
})

describe('failedResponseError parses JSON body', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: '  not found  ', code: '  missing  ' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('maps message and code from JSON error payload', async () => {
    await expect(getCourse('missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'not found',
      code: 'missing',
    })
  })
})

describe('getUploadUrl error response', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: 'quota', code: 'rate_limited' }), {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })
  it('throws ApiError from upload-url failure', async () => {
    await expect(getUploadUrl('f.png', 'image/png', { courseId: 'c1', uploadKind: 'thumbnail' })).rejects.toMatchObject({
      status: 429,
      message: 'quota',
      code: 'rate_limited',
    })
  })
})
