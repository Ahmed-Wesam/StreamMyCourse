import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())
const loadTokensMock = vi.hoisted(() => vi.fn())
const setClientMetadataProviderMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth/cognito', () => ({
  cognitoUserPoolsTokenProvider: {
    authTokenStore: {
      loadTokens: loadTokensMock,
    },
    setClientMetadataProvider: setClientMetadataProviderMock,
  },
}))

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

import {
  enterSupersededState,
  resetStudentSessionSupersededForTests,
} from './student-session-superseded'
import {
  registerStudentSessionRefreshMetadata,
  resetStudentSessionRefreshRegistrationForTests,
  studentSessionIdFromIdToken,
  STUDENT_SESSION_METADATA_KEY,
} from './student-session-refresh'

describe('studentSessionIdFromIdToken', () => {
  it('reads student_session_id claim', () => {
    expect(
      studentSessionIdFromIdToken({
        payload: { student_session_id: 'abc-123' },
        toString: () => 'jwt',
      }),
    ).toBe('abc-123')
  })

  it('falls back to custom:student_session_id', () => {
    expect(
      studentSessionIdFromIdToken({
        payload: { 'custom:student_session_id': 'def-456' },
        toString: () => 'jwt',
      }),
    ).toBe('def-456')
  })

  it('returns undefined when claim missing', () => {
    expect(studentSessionIdFromIdToken(undefined)).toBeUndefined()
    expect(studentSessionIdFromIdToken({ payload: {}, toString: () => 'jwt' })).toBeUndefined()
  })
})

describe('registerStudentSessionRefreshMetadata', () => {
  beforeEach(() => {
    resetStudentSessionRefreshRegistrationForTests()
    resetStudentSessionSupersededForTests()
    fetchAuthSessionMock.mockReset()
    loadTokensMock.mockReset()
    setClientMetadataProviderMock.mockReset()
  })

  it('registers provider once and supplies student_session_id from cached tokens', async () => {
    loadTokensMock.mockResolvedValue({
      idToken: { payload: { student_session_id: 'sess-1' }, toString: () => 'jwt' },
    })

    registerStudentSessionRefreshMetadata()
    registerStudentSessionRefreshMetadata()
    expect(setClientMetadataProviderMock).toHaveBeenCalledTimes(1)

    const provider = setClientMetadataProviderMock.mock.calls[0][0] as () => Promise<Record<string, string>>
    await expect(provider()).resolves.toEqual({ [STUDENT_SESSION_METADATA_KEY]: 'sess-1' })
    expect(loadTokensMock).toHaveBeenCalledTimes(1)
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })

  it('returns empty object when cached id token has no session claim', async () => {
    loadTokensMock.mockResolvedValue({
      idToken: { payload: {}, toString: () => 'jwt' },
    })

    registerStudentSessionRefreshMetadata()
    const provider = setClientMetadataProviderMock.mock.calls[0][0] as () => Promise<Record<string, string>>
    await expect(provider()).resolves.toEqual({})
    expect(loadTokensMock).toHaveBeenCalledTimes(1)
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })

  it('returns empty object while student session is superseded', async () => {
    registerStudentSessionRefreshMetadata()
    const provider = setClientMetadataProviderMock.mock.calls[0][0] as () => Promise<Record<string, string>>
    enterSupersededState()
    await expect(provider()).resolves.toEqual({})
    expect(loadTokensMock).not.toHaveBeenCalled()
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })
})
