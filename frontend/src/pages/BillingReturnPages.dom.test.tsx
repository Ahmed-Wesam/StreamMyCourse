/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const billingApi = vi.hoisted(() => ({
  getCheckoutStatus: vi.fn(),
}))

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/billing')>()
  return {
    ...mod,
    getCheckoutStatus: (...args: unknown[]) => billingApi.getCheckoutStatus(...args),
  }
})

import BillingResultPage from './BillingResultPage'
import { BillingCancelRedirect, BillingSuccessRedirect } from './BillingLegacyRedirect'
import {
  billingConfirmingMessage,
  billingEnrolledMessage,
  billingPaymentFailedMessage,
} from '../lib/purchaseCopy'
import { setCheckoutPendingContext } from '../lib/checkoutPendingPurchase'

function renderResult(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/billing/result" element={<BillingResultPage />} />
        <Route path="/billing/success" element={<BillingSuccessRedirect />} />
        <Route path="/billing/cancel" element={<BillingCancelRedirect />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Billing return pages', () => {
  beforeEach(() => {
    billingApi.getCheckoutStatus.mockReset()
    sessionStorage.clear()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    sessionStorage.clear()
  })

  it('polls checkout-status with purchaseId while pending', async () => {
    setCheckoutPendingContext({
      purchaseId: 'p-pending',
      productType: 'bundle',
    })
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'pending' })

    renderResult('/billing/result?id=CHK-IGNORED')

    await waitFor(() => {
      expect(billingApi.getCheckoutStatus).toHaveBeenCalledWith('p-pending')
    })
    expect(screen.getByRole('heading', { name: billingConfirmingMessage })).toBeTruthy()
    expect(billingApi.getCheckoutStatus).not.toHaveBeenCalledWith('CHK-IGNORED')
  })

  it('shows enrolled copy and course link when status becomes paid', async () => {
    setCheckoutPendingContext({
      purchaseId: 'p-paid',
      productType: 'course',
      courseId: 'c-42',
    })
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'paid' })

    renderResult('/billing/result')

    expect(await screen.findByRole('heading', { name: billingEnrolledMessage })).toBeTruthy()
    const link = screen.getByRole('link', { name: /continue to your course/i })
    expect(link.getAttribute('href')).toBe('/courses/c-42')
  })

  it('shows enrolled dashboard link for bundle checkout', async () => {
    setCheckoutPendingContext({
      purchaseId: 'p-bundle',
      productType: 'bundle',
    })
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'paid' })

    renderResult('/billing/result')

    expect(await screen.findByRole('heading', { name: billingEnrolledMessage })).toBeTruthy()
    const link = screen.getByRole('link', { name: /go to dashboard/i })
    expect(link.getAttribute('href')).toBe('/dashboard')
  })

  it('shows failed copy when status is failed', async () => {
    setCheckoutPendingContext({
      purchaseId: 'p-fail',
      productType: 'bundle',
    })
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'failed' })

    renderResult('/billing/result')

    expect(await screen.findByRole('heading', { name: billingPaymentFailedMessage })).toBeTruthy()
  })

  it('redirects legacy success route to result', async () => {
    setCheckoutPendingContext({ purchaseId: 'p1', productType: 'bundle' })
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'pending' })

    renderResult('/billing/success?id=CHK-99')

    expect(await screen.findByTestId('billing-result-page')).toBeTruthy()
  })
})
