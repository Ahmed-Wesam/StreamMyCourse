/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const billingApi = vi.hoisted(() => ({
  getCheckoutStatus: vi.fn(),
  getPurchases: vi.fn(),
}))

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/billing')>()
  return {
    ...mod,
    getCheckoutStatus: (...args: unknown[]) => billingApi.getCheckoutStatus(...args),
    getPurchases: (...args: unknown[]) => billingApi.getPurchases(...args),
  }
})

import BillingResultPage from './BillingResultPage'
import { BillingCancelRedirect, BillingSuccessRedirect } from './BillingLegacyRedirect'
import { billingCancelMessage, billingSuccessMessage } from '../lib/purchaseCopy'

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
    billingApi.getPurchases.mockReset()
    sessionStorage.clear()
    billingApi.getCheckoutStatus.mockResolvedValue({ status: 'ok' })
    billingApi.getPurchases.mockResolvedValue([
      {
        id: 'p1',
        productType: 'bundle',
        status: 'paid',
        amountMinor: 150_000,
        currency: 'JOD',
        createdAt: '2026-01-01T00:00:00Z',
      },
    ])
  })

  afterEach(() => {
    cleanup()
  })

  it('confirms payment via checkout-status and paid purchases', async () => {
    sessionStorage.setItem('streammycourse.checkoutPendingPurchaseId', 'p1')
    renderResult('/billing/result?id=MOCK-HP-CHECKOUT')

    await waitFor(() => {
      expect(billingApi.getCheckoutStatus).toHaveBeenCalledWith('MOCK-HP-CHECKOUT')
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })

    expect(await screen.findByRole('heading', { name: /Payment received/i })).toBeTruthy()
    expect(screen.getByText(billingSuccessMessage)).toBeTruthy()
    expect(screen.queryByText(/access granted/i)).toBeNull()
  })

  it('does not treat an older paid purchase as success for a new checkout', async () => {
    sessionStorage.setItem('streammycourse.checkoutPendingPurchaseId', 'p2-new')
    billingApi.getPurchases.mockResolvedValue([
      {
        id: 'p1',
        productType: 'bundle',
        status: 'paid',
        amountMinor: 150_000,
        currency: 'JOD',
        createdAt: '2026-01-01T00:00:00Z',
      },
      {
        id: 'p2-new',
        productType: 'course',
        courseId: 'c9',
        status: 'pending',
        amountMinor: 50_000,
        currency: 'JOD',
        createdAt: '2026-01-02T00:00:00Z',
      },
    ])

    renderResult('/billing/result?id=MOCK-HP-CHECKOUT')

    await waitFor(() => {
      expect(billingApi.getCheckoutStatus).toHaveBeenCalled()
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(billingApi.getPurchases.mock.calls.length).toBeGreaterThan(0)
    })
    expect(screen.queryByRole('heading', { name: /Payment received/i })).toBeNull()
  })

  it('shows cancel copy when redirected from legacy cancel route', async () => {
    renderResult('/billing/cancel')

    expect(await screen.findByRole('heading', { name: /Checkout canceled/i })).toBeTruthy()
    expect(screen.getByText(billingCancelMessage)).toBeTruthy()
    expect(billingApi.getCheckoutStatus).not.toHaveBeenCalled()
  })

  it('redirects legacy success route to result with query preserved', async () => {
    renderResult('/billing/success?id=CHK-99')

    expect(await screen.findByTestId('billing-result-page')).toBeTruthy()
    await waitFor(() => {
      expect(billingApi.getCheckoutStatus).toHaveBeenCalledWith('CHK-99')
    })
  })
})
