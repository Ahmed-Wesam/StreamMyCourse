/**
 * @vitest-environment jsdom
 */
import { render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../../lib/api'
import { StudentProfileBootstrap } from './StudentProfileBootstrap'

const mockAuthStatus = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: () => ({ authStatus: mockAuthStatus() }),
}))

describe('StudentProfileBootstrap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStatus.mockReturnValue('unauthenticated')
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
})
