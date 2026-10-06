/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const billingApi = vi.hoisted(() => ({
  getPurchases: vi.fn(),
}))

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/billing')>()
  return {
    ...mod,
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
    billingApi.getPurchases.mockReset()
    sessionStorage.clear()
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

  it('confirms payment when purchases show paid after webhook fulfillment', async () => {
    sessionStorage.setItem('streammycourse.checkoutPendingPurchaseId', 'p1')
    renderResult('/billing/result?id=MOCK-HP-CHECKOUT')

    await waitFor(() => {
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })

    expect(await screen.findByRole('heading', { name: /Payment received/i })).toBeTruthy()
    expect(screen.getByText(billingSuccessMessage)).toBeTruthy()
    expect(screen.queryByText(/access granted/i)).toBeNull()
  })

  it('does not treat any paid purchase as success when pending id is missing', async () => {
    sessionStorage.clear()
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
    renderResult('/billing/result?id=MOCK-HP-CHECKOUT')

    await waitFor(() => {
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })
    expect(screen.queryByRole('heading', { name: /Payment received/i })).toBeNull()
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
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })
    expect(screen.queryByRole('heading', { name: /Payment received/i })).toBeNull()
  })

  it('tells the shopper to stay on the page while waiting for webhook fulfillment', async () => {
    billingApi.getPurchases.mockResolvedValue([])
    renderResult('/billing/result?id=CHK-1')

    expect(await screen.findByText(/Do not leave this page/i)).toBeTruthy()
    expect(screen.queryByRole('link', { name: /browse courses/i })).toBeNull()
  })

  it('shows cancel copy when redirected from legacy cancel route', async () => {
    renderResult('/billing/cancel')

    expect(await screen.findByRole('heading', { name: /Checkout canceled/i })).toBeTruthy()
    expect(screen.getByText(billingCancelMessage)).toBeTruthy()
  })

  it('redirects legacy success route to result with query preserved', async () => {
    billingApi.getPurchases.mockResolvedValue([])
    renderResult('/billing/success?id=CHK-99')

    expect(await screen.findByTestId('billing-result-page')).toBeTruthy()
    await waitFor(() => {
      expect(billingApi.getPurchases).toHaveBeenCalled()
    })
  })
})
