import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())
const setClientMetadataProviderMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth/cognito', () => ({
  cognitoUserPoolsTokenProvider: {
    setClientMetadataProvider: setClientMetadataProviderMock,
  },
}))

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

import {
  armSessionSupersedeHandling,
  resetSessionSupersedeHandlingForTests,
} from './session-supersede-handling'
import {
  buildStudentRefreshClientMetadata,
  registerStudentSessionRefreshMetadata,
  resetStudentSessionRefreshRegistrationForTests,
  studentSessionIdFromIdToken,
  STUDENT_SESSION_METADATA_KEY,
  restoreStudentSessionRefreshMetadata,
  suspendStudentSessionRefreshMetadata,
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
    resetSessionSupersedeHandlingForTests()
    fetchAuthSessionMock.mockReset()
    setClientMetadataProviderMock.mockReset()
  })

  it('registers provider once and supplies student_session_id metadata', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { student_session_id: 'sess-1' }, toString: () => 'jwt' } },
    })

    registerStudentSessionRefreshMetadata()
    registerStudentSessionRefreshMetadata()
    expect(setClientMetadataProviderMock).toHaveBeenCalledTimes(1)

    const provider = setClientMetadataProviderMock.mock.calls[0][0] as () => Promise<Record<string, string>>
    await expect(provider()).resolves.toEqual({ [STUDENT_SESSION_METADATA_KEY]: 'sess-1' })
  })

  it('buildStudentRefreshClientMetadata returns empty object when claim missing', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: {}, toString: () => 'jwt' } },
    })
    await expect(buildStudentRefreshClientMetadata()).resolves.toEqual({})
  })

  it('skips fetchAuthSession while supersede handling is armed', async () => {
    registerStudentSessionRefreshMetadata()
    const provider = setClientMetadataProviderMock.mock.calls[0][0] as () => Promise<Record<string, string>>
    armSessionSupersedeHandling()
    await expect(provider()).resolves.toEqual({})
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })

  it('suspendStudentSessionRefreshMetadata uses a no-op provider', async () => {
    registerStudentSessionRefreshMetadata()
    suspendStudentSessionRefreshMetadata()
    const provider = setClientMetadataProviderMock.mock.calls.at(-1)?.[0] as () => Promise<Record<string, string>>
    await expect(provider()).resolves.toEqual({})
    expect(fetchAuthSessionMock).not.toHaveBeenCalled()
  })

  it('restoreStudentSessionRefreshMetadata re-attaches token metadata provider', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { student_session_id: 'sess-1' }, toString: () => 'jwt' } },
    })
    registerStudentSessionRefreshMetadata()
    suspendStudentSessionRefreshMetadata()
    restoreStudentSessionRefreshMetadata()
    const provider = setClientMetadataProviderMock.mock.calls.at(-1)?.[0] as () => Promise<Record<string, string>>
    await expect(provider()).resolves.toEqual({ student_session_id: 'sess-1' })
  })
})
