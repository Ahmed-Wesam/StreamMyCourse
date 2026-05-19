/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

import {
  providerCancelRetryStorageKey,
  clearProviderCancelRetryFlag,
  readProviderCancelRetryFlag,
  setProviderCancelRetryFlag,
} from './billingProviderCancelRetry'

const USER_SUB = 'cognito-sub-1'

describe('billingProviderCancelRetry', () => {
  afterEach(() => {
    clearProviderCancelRetryFlag(USER_SUB)
    vi.clearAllMocks()
  })

  it('persists retry flag per user in sessionStorage', () => {
    expect(readProviderCancelRetryFlag(USER_SUB)).toBe(false)
    setProviderCancelRetryFlag(USER_SUB)
    expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBe('1')
    expect(readProviderCancelRetryFlag(USER_SUB)).toBe(true)
    expect(readProviderCancelRetryFlag('other-sub')).toBe(false)
    clearProviderCancelRetryFlag(USER_SUB)
    expect(readProviderCancelRetryFlag(USER_SUB)).toBe(false)
  })

  it('readCognitoSubFromSession returns sub from id token payload', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { sub: USER_SUB } } },
    })
    const { readCognitoSubFromSession } = await import('./billingProviderCancelRetry')
    await expect(readCognitoSubFromSession()).resolves.toBe(USER_SUB)
  })
})
