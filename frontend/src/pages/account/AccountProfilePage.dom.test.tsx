/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMeMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/session', () => ({
  fetchMe: (...args: unknown[]) => fetchMeMock(...args),
}))

const billingApi = vi.hoisted(() => ({
  getSubscription: vi.fn(),
}))

vi.mock('../../lib/api/billing', () => ({
  getSubscription: (...args: unknown[]) => billingApi.getSubscription(...args),
}))

import AccountProfilePage from './AccountProfilePage'

const profile = {
  userId: 'user-1',
  email: 'student@example.com',
  role: 'student',
  cognitoSub: 'sub-1',
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
}

describe('AccountProfilePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  beforeEach(() => {
    fetchMeMock.mockReset()
    billingApi.getSubscription.mockReset()
  })

  it('shows profile email from fetchMe', async () => {
    fetchMeMock.mockResolvedValue(profile)

    render(<AccountProfilePage />)

    expect(await screen.findByText('student@example.com')).toBeTruthy()
  })

  it('renders static Security and Notifications cards without editable controls', async () => {
    fetchMeMock.mockResolvedValue(profile)

    const { container } = render(<AccountProfilePage />)

    await waitFor(() => {
      expect(screen.getByText('student@example.com')).toBeTruthy()
    })

    expect(screen.getByRole('heading', { name: /security/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /notification preferences/i })).toBeTruthy()
    expect(container.querySelector('input')).toBeNull()
    expect(container.querySelector('textarea')).toBeNull()
    expect(container.querySelector('input[type="file"]')).toBeNull()
  })

  it('does not call billing APIs from profile dummy cards', async () => {
    fetchMeMock.mockResolvedValue(profile)

    render(<AccountProfilePage />)

    await waitFor(() => {
      expect(screen.getByText('student@example.com')).toBeTruthy()
    })

    expect(billingApi.getSubscription).not.toHaveBeenCalled()
  })
})
