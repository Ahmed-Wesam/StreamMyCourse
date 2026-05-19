/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import type { MerchantStatusResponse } from '../lib/billing'
import TeacherPaymentSetup from './TeacherPaymentSetup'

const billing = vi.hoisted(() => ({
  getMerchantStatus: vi.fn(),
}))

vi.mock('../lib/billing', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/billing')
  return {
    ...mod,
    getMerchantStatus: (...args: unknown[]) =>
      billing.getMerchantStatus(...args) as ReturnType<typeof mod.getMerchantStatus>,
  }
})

const pendingStatus: MerchantStatusResponse = {
  provider: 'paytabs',
  providerProfileId: 'mock-profile',
  payoutReady: false,
  payoutReadyAt: null,
  setupChecklist: {
    paytabsAccountCreated: false,
    profileIdConfigured: true,
    repeatBillingEnabled: false,
    termsUrlSet: false,
    ipnRegistered: false,
    testChargeSucceeded: false,
    payoutMarkedReady: false,
  },
}

const readyStatus: MerchantStatusResponse = {
  provider: 'paytabs',
  providerProfileId: 'pt-live-profile-99',
  payoutReady: true,
  payoutReadyAt: '2026-05-01T12:00:00Z',
  setupChecklist: {
    paytabsAccountCreated: true,
    profileIdConfigured: true,
    repeatBillingEnabled: false,
    termsUrlSet: false,
    ipnRegistered: false,
    testChargeSucceeded: false,
    payoutMarkedReady: true,
  },
}

function renderPaymentSetup(initialEntries: string[] = ['/settings/payments']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/settings/payments" element={<TeacherPaymentSetup />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TeacherPaymentSetup', () => {
  beforeEach(() => {
    billing.getMerchantStatus.mockReset()
    billing.getMerchantStatus.mockResolvedValue(pendingStatus)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('shows pending checklist items when payout is not ready', async () => {
    renderPaymentSetup()

    await waitFor(() => {
      expect(billing.getMerchantStatus).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByTestId('merchant-payout-status').textContent).toMatch(/setup in progress/i)
    expect(screen.getByTestId('checklist-repeatBillingEnabled').textContent).toMatch(/pending/i)
    expect(screen.getByTestId('checklist-payoutMarkedReady').textContent).toMatch(/pending/i)
    expect(screen.getByTestId('checklist-profileIdConfigured').textContent).toMatch(/complete/i)
    expect(screen.getByTestId('checklist-paytabsAccountCreated').textContent).toMatch(/pending/i)
  })

  it('shows ready checklist when payout is ready', async () => {
    billing.getMerchantStatus.mockResolvedValue(readyStatus)
    renderPaymentSetup()

    await waitFor(() => {
      expect(screen.getByTestId('merchant-payout-status').textContent).toMatch(/payout ready/i)
    })

    expect(screen.getByTestId('checklist-payoutMarkedReady').textContent).toMatch(/complete/i)
    expect(screen.getByTestId('checklist-profileIdConfigured').textContent).toMatch(/complete/i)
    expect(screen.getByTestId('checklist-testChargeSucceeded').textContent).toMatch(/pending/i)
    expect(screen.getByTestId('checklist-repeatBillingEnabled').textContent).toMatch(/pending/i)
  })

  it('shows a permission message when merchant status returns 403', async () => {
    billing.getMerchantStatus.mockRejectedValue(new ApiError('Forbidden', 403, 'forbidden'))
    renderPaymentSetup()

    await waitFor(() => {
      expect(
        screen.getByText(/only the designated billing teacher can view payment setup/i),
      ).toBeTruthy()
    })
  })

  it('links to PayTabs docs and refresh reloads status', async () => {
    renderPaymentSetup()

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /going live/i })).toBeTruthy()
    })

    const goingLive = screen.getByRole('link', { name: /going live/i })
    expect(goingLive.getAttribute('href')).toContain('paytabs.com')
    expect(goingLive.getAttribute('target')).toBe('_blank')

    const apiKeys = screen.getByRole('link', { name: /api keys/i })
    expect(apiKeys.getAttribute('href')).toContain('paytabs.com')

    expect(screen.getByText(/jordanian dinar \(jod\)/i)).toBeTruthy()
    expect(screen.getByText(/merchant of record/i)).toBeTruthy()

    billing.getMerchantStatus.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /refresh status/i }))

    await waitFor(() => {
      expect(billing.getMerchantStatus).toHaveBeenCalledTimes(1)
    })
  })
})
