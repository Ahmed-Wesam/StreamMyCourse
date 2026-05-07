/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())
const isAuthConfiguredMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

vi.mock('./auth', () => ({
  isAuthConfigured: () => isAuthConfiguredMock(),
}))

import { hasSignedInIdToken } from './api'

describe('hasSignedInIdToken', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns false when auth is not configured', async () => {
    isAuthConfiguredMock.mockReturnValue(false)
    expect(await hasSignedInIdToken()).toBe(false)
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })

  it('returns true when configured and session has id token string', async () => {
    isAuthConfiguredMock.mockReturnValue(true)
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: '  tok  ' } })
    expect(await hasSignedInIdToken()).toBe(true)
  })

  it('returns false when session has no usable token', async () => {
    isAuthConfiguredMock.mockReturnValue(true)
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
    expect(await hasSignedInIdToken()).toBe(false)
  })

  it('returns false when fetchAuthSession throws', async () => {
    isAuthConfiguredMock.mockReturnValue(true)
    fetchAuthSessionMock.mockRejectedValue(new Error('offline'))
    expect(await hasSignedInIdToken()).toBe(false)
  })
})
