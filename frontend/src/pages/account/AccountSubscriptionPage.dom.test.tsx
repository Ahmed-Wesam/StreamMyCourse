/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../lib/api'

const api = vi.hoisted(() => ({
  getSubscription: vi.fn(),
  cancelSubscription: vi.fn(),
  reactivateSubscription: vi.fn(),
}))

vi.mock('../../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../../lib/api')
  return {
    ...mod,
    getSubscription: (...args: unknown[]) =>
      api.getSubscription(...args) as ReturnType<typeof mod.getSubscription>,
    cancelSubscription: (...args: unknown[]) =>
      api.cancelSubscription(...args) as ReturnType<typeof mod.cancelSubscription>,
    reactivateSubscription: (...args: unknown[]) =>
      api.reactivateSubscription(...args) as ReturnType<typeof mod.reactivateSubscription>,
  }
})

import AccountSubscriptionPage from './AccountSubscriptionPage'

describe('AccountSubscriptionPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  beforeEach(() => {
    api.getSubscription.mockReset()
    api.cancelSubscription.mockReset()
    api.reactivateSubscription.mockReset()
  })

  it('shows not subscribed state on 404 not_subscribed', async () => {
    api.getSubscription.mockRejectedValue(new ApiError('No active subscription to manage', 404, 'not_subscribed'))

    render(
      <MemoryRouter>
        <AccountSubscriptionPage />
      </MemoryRouter>,
    )

    expect(await screen.findByTestId('subscription-not-subscribed')).toBeTruthy()
    expect(screen.getByRole('link', { name: /browse courses/i }).getAttribute('href')).toBe('/courses')
  })

  it('shows subscription summary with cancel when canCancel', async () => {
    api.getSubscription.mockResolvedValue({
      status: 'active',
      currentPeriodEnd: '2026-06-18T00:00:00.000Z',
      cancelAtPeriodEnd: false,
      canCancel: true,
      canReactivate: false,
      nextBillingDate: '2026-06-18T00:00:00.000Z',
      amountMinor: 50000,
      currency: 'JOD',
      planLabel: '50 JOD / month',
      pastDue: false,
    })

    render(
      <MemoryRouter>
        <AccountSubscriptionPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('subscription-status').textContent).toMatch(/active/i)
    })
    expect(screen.getByTestId('subscription-amount').textContent).toBe('50 JOD / month')
    expect(screen.getByTestId('subscription-cancel-btn')).toBeTruthy()
  })
})
