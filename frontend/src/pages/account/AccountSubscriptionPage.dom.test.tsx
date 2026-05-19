/**

 * @vitest-environment jsdom

 */

import { cleanup, render, screen, waitFor } from '@testing-library/react'

import { MemoryRouter } from 'react-router-dom'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'



import { ApiError } from '../../lib/api'

import {

  providerCancelRetryStorageKey,

  clearProviderCancelRetryFlag,

  setProviderCancelRetryFlag,

} from '../../lib/billingProviderCancelRetry'



const USER_SUB = 'cognito-sub-1'



const api = vi.hoisted(() => ({

  getSubscription: vi.fn(),

  cancelSubscription: vi.fn(),

}))



const billingRetry = vi.hoisted(() => ({

  readCognitoSubFromSession: vi.fn(),

}))



vi.mock('../../lib/api', async (importOriginal) => {

  const mod = (await importOriginal()) as typeof import('../../lib/api')

  return {

    ...mod,

    getSubscription: (...args: unknown[]) =>

      api.getSubscription(...args) as ReturnType<typeof mod.getSubscription>,

    cancelSubscription: (...args: unknown[]) =>

      api.cancelSubscription(...args) as ReturnType<typeof mod.cancelSubscription>,

  }

})



vi.mock('../../lib/billingProviderCancelRetry', async (importOriginal) => {

  const mod = (await importOriginal()) as typeof import('../../lib/billingProviderCancelRetry')

  return {

    ...mod,

    readCognitoSubFromSession: () => billingRetry.readCognitoSubFromSession(),

  }

})



import AccountSubscriptionPage from './AccountSubscriptionPage'



const canceledSummary = {

  status: 'canceled' as const,

  currentPeriodEnd: '2026-06-18T00:00:00.000Z',

  cancelAtPeriodEnd: true,

  canCancel: false,

  nextBillingDate: null,

  amountMinor: 50000,

  currency: 'JOD',

  planLabel: '50 JOD / month',

  pastDue: false,

}



describe('AccountSubscriptionPage', () => {

  afterEach(() => {

    cleanup()

    vi.clearAllMocks()

    clearProviderCancelRetryFlag(USER_SUB)

  })



  beforeEach(() => {

    api.getSubscription.mockReset()

    api.cancelSubscription.mockReset()

    billingRetry.readCognitoSubFromSession.mockResolvedValue(USER_SUB)

    clearProviderCancelRetryFlag(USER_SUB)

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

    expect(screen.getByTestId('subscription-cancel-btn')).toBeTruthy()

  })



  it('shows retry button when canceled-in-period and session retry flag is set for user', async () => {

    setProviderCancelRetryFlag(USER_SUB)

    api.getSubscription.mockResolvedValue(canceledSummary)



    render(

      <MemoryRouter>

        <AccountSubscriptionPage />

      </MemoryRouter>,

    )



    await waitFor(() => {

      expect(screen.getByTestId('subscription-retry-provider-cancel-btn')).toBeTruthy()

    })

    expect(screen.queryByTestId('subscription-cancel-btn')).toBeNull()

    expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBe('1')

  })



  it('syncs subscription and shows retry after provider_cancel_failed', async () => {

    api.getSubscription

      .mockResolvedValueOnce({

        status: 'active',

        currentPeriodEnd: '2026-06-18T00:00:00.000Z',

        cancelAtPeriodEnd: false,

        canCancel: true,

        nextBillingDate: '2026-06-18T00:00:00.000Z',

        amountMinor: 50000,

        currency: 'JOD',

        planLabel: '50 JOD / month',

        pastDue: false,

      })

      .mockResolvedValueOnce(canceledSummary)

    api.cancelSubscription.mockRejectedValue(

      new ApiError('Unable to cancel subscription with payment provider', 502, 'provider_cancel_failed'),

    )



    render(

      <MemoryRouter>

        <AccountSubscriptionPage />

      </MemoryRouter>,

    )



    await waitFor(() => {

      expect(screen.getByTestId('subscription-cancel-btn')).toBeTruthy()

    })



    screen.getByTestId('subscription-cancel-btn').click()



    await waitFor(() => {

      expect(screen.getByTestId('subscription-retry-provider-cancel-btn')).toBeTruthy()

    })

    expect(screen.getByTestId('subscription-status').textContent).toMatch(/canceled/i)

    expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBe('1')

  })



  it('clears retry flag and button after successful retry', async () => {

    setProviderCancelRetryFlag(USER_SUB)

    api.getSubscription.mockResolvedValue(canceledSummary)

    api.cancelSubscription.mockResolvedValue({

      status: 'canceled',

      cancelAtPeriodEnd: true,

      currentPeriodEnd: '2026-06-18T00:00:00.000Z',

    })



    render(

      <MemoryRouter>

        <AccountSubscriptionPage />

      </MemoryRouter>,

    )



    await waitFor(() => {

      expect(screen.getByTestId('subscription-retry-provider-cancel-btn')).toBeTruthy()

    })



    screen.getByTestId('subscription-retry-provider-cancel-btn').click()



    await waitFor(() => {

      expect(screen.queryByTestId('subscription-retry-provider-cancel-btn')).toBeNull()

    })

    expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBeNull()

  })



  it('persists retry flag on provider_cancel_failed when userSub resolves during cancel', async () => {
    billingRetry.readCognitoSubFromSession
      .mockResolvedValueOnce(null)
      .mockResolvedValue(USER_SUB)
    api.getSubscription
      .mockResolvedValueOnce({
        status: 'active',
        currentPeriodEnd: '2026-06-18T00:00:00.000Z',
        cancelAtPeriodEnd: false,
        canCancel: true,
        nextBillingDate: '2026-06-18T00:00:00.000Z',
        amountMinor: 50000,
        currency: 'JOD',
        planLabel: '50 JOD / month',
        pastDue: false,
      })
      .mockResolvedValueOnce(canceledSummary)
    api.cancelSubscription.mockRejectedValue(
      new ApiError('Unable to cancel subscription with payment provider', 502, 'provider_cancel_failed'),
    )

    render(
      <MemoryRouter>
        <AccountSubscriptionPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('subscription-cancel-btn')).toBeTruthy()
    })

    screen.getByTestId('subscription-cancel-btn').click()

    await waitFor(() => {
      expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBe('1')
    })
    expect(billingRetry.readCognitoSubFromSession).toHaveBeenCalledTimes(2)
  })

  it('clears retry flag on provider_agreement_missing', async () => {

    setProviderCancelRetryFlag(USER_SUB)

    api.getSubscription.mockResolvedValue(canceledSummary)

    api.cancelSubscription.mockRejectedValue(

      new ApiError('Subscription is canceled but no payment agreement is on file', 502, 'provider_agreement_missing'),

    )



    render(

      <MemoryRouter>

        <AccountSubscriptionPage />

      </MemoryRouter>,

    )



    await waitFor(() => {

      expect(screen.getByTestId('subscription-retry-provider-cancel-btn')).toBeTruthy()

    })



    screen.getByTestId('subscription-retry-provider-cancel-btn').click()



    await waitFor(() => {

      expect(screen.queryByTestId('subscription-retry-provider-cancel-btn')).toBeNull()

    })

    expect(sessionStorage.getItem(providerCancelRetryStorageKey(USER_SUB))).toBeNull()

    expect(screen.getByRole('alert').textContent).toMatch(/contact support/i)

  })

})


