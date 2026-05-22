/**
 * @vitest-environment jsdom
 */
import { render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../../lib/api/session'
import { StudentProfileBootstrap } from './StudentProfileBootstrap'

const mockAuthStatus = vi.hoisted(() => vi.fn())
const markUserProfileWarmed = vi.hoisted(() => vi.fn())

vi.mock('../../lib/auth-ui', () => ({
  useAuthenticator: () => ({ authStatus: mockAuthStatus() }),
}))

vi.mock('../../lib/auth-session-lazy', () => ({
  markUserProfileWarmed: () => markUserProfileWarmed(),
}))

describe('StudentProfileBootstrap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStatus.mockReturnValue('unauthenticated')
    markUserProfileWarmed.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls fetchMe once when auth becomes authenticated', async () => {
    const fetchMe = vi.spyOn(api, 'fetchMe').mockResolvedValue({
      userId: 'u1',
      email: 'a@b.com',
      role: 'student',
      cognitoSub: 'u1',
      createdAt: '',
      updatedAt: '',
    })
    const { rerender } = render(<StudentProfileBootstrap />)
    expect(fetchMe).not.toHaveBeenCalled()

    mockAuthStatus.mockReturnValue('authenticated')
    rerender(<StudentProfileBootstrap />)

    await waitFor(() => {
      expect(fetchMe).toHaveBeenCalledTimes(1)
      expect(markUserProfileWarmed).toHaveBeenCalledTimes(1)
    })

    rerender(<StudentProfileBootstrap />)
    expect(fetchMe).toHaveBeenCalledTimes(1)
  })

  it('resets when user signs out', async () => {
    const fetchMe = vi.spyOn(api, 'fetchMe').mockResolvedValue({
      userId: 'u1',
      email: 'a@b.com',
      role: 'student',
      cognitoSub: 'u1',
      createdAt: '',
      updatedAt: '',
    })
    mockAuthStatus.mockReturnValue('authenticated')
    const { rerender } = render(<StudentProfileBootstrap />)
    await waitFor(() => expect(fetchMe).toHaveBeenCalledTimes(1))

    mockAuthStatus.mockReturnValue('unauthenticated')
    rerender(<StudentProfileBootstrap />)
    mockAuthStatus.mockReturnValue('authenticated')
    rerender(<StudentProfileBootstrap />)
    await waitFor(() => expect(fetchMe).toHaveBeenCalledTimes(2))
  })

  it('ignores fetchMe rejection (non-fatal bootstrap)', async () => {
    const fetchMe = vi.spyOn(api, 'fetchMe').mockRejectedValue(new Error('not provisioned'))
    mockAuthStatus.mockReturnValue('authenticated')
    render(<StudentProfileBootstrap />)
    await waitFor(() => expect(fetchMe).toHaveBeenCalledTimes(1))
    expect(markUserProfileWarmed).not.toHaveBeenCalled()
  })
})
