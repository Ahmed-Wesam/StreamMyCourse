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
