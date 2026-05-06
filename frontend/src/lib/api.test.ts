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

import { ApiError, getCourse, isPlaybackAuthRequiredError, listLessons } from './api'

describe('catalog GET without signed-in session', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === 'string' ? input : input.toString()
        const body = url.includes('/lessons') ? [] : { id: 'x', title: 'T', description: 'D', status: 'PUBLISHED' }
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

import {
  getCourseProgress,
  updateLessonProgress,
  isProgressRdsUnavailableError,
  isProgressAuthNotConfiguredError,
} from './api'

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
