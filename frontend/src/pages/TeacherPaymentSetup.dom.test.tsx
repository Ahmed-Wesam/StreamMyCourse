/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api/client'
import type { MerchantStatusResponse } from '../lib/billing'
import TeacherPaymentSetup from './TeacherPaymentSetup'

const billing = vi.hoisted(() => ({
  getMerchantStatus: vi.fn(),
}))

const billingApi = vi.hoisted(() => ({
  getBundle: vi.fn(),
}))

const pricingApi = vi.hoisted(() => ({
  setBundlePrice: vi.fn(),
}))

vi.mock('../lib/billing', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/billing')
  return {
    ...mod,
    getMerchantStatus: (...args: unknown[]) =>
      billing.getMerchantStatus(...args) as ReturnType<typeof mod.getMerchantStatus>,
  }
})

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/billing')
  return {
    ...mod,
    getBundle: (...args: unknown[]) => billingApi.getBundle(...args) as ReturnType<typeof mod.getBundle>,
  }
})

vi.mock('../lib/api/pricing', () => ({
  setBundlePrice: (...args: unknown[]) => pricingApi.setBundlePrice(...args),
}))

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

const FORBIDDEN_CLASS_SUBSTRINGS = [
  'emerald-',
  'blue-600',
  'green-',
  'gray-',
  'slate-',
  'amber-',
] as const

function collectClassNames(root: Element): string[] {
  const names: string[] = []
  const walk = (el: Element) => {
    if (typeof el.className === 'string' && el.className.length > 0) {
      names.push(el.className)
    }
    for (const child of el.children) {
      walk(child)
    }
  }
  walk(root)
  return names
}

function findForbiddenPaletteClasses(classNames: string[]): string[] {
  const hits: string[] = []
  for (const cn of classNames) {
    for (const forbidden of FORBIDDEN_CLASS_SUBSTRINGS) {
      if (cn.includes(forbidden)) {
        hits.push(`${forbidden} → ${cn}`)
      }
    }
  }
  return hits
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
    billingApi.getBundle.mockReset()
    billingApi.getBundle.mockResolvedValue({ amountMinor: 15000, currency: 'USD' })
    pricingApi.setBundlePrice.mockReset()
    pricingApi.setBundlePrice.mockResolvedValue({ amountMinor: 12000, currency: 'USD' })
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
    expect(screen.queryByTestId('checklist-repeatBillingEnabled')).toBeNull()
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
    expect(screen.queryByTestId('checklist-repeatBillingEnabled')).toBeNull()
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

  it('shows student-site PayTabs URLs from VITE_STUDENT_SITE_URL, not teacher origin', async () => {
    vi.stubEnv('VITE_STUDENT_SITE_URL', 'https://example-student.test')
    vi.resetModules()
    const { default: PaymentSetup } = await import('./TeacherPaymentSetup')

    render(
      <MemoryRouter initialEntries={['/settings/payments']}>
        <Routes>
          <Route path="/settings/payments" element={<PaymentSetup />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(billing.getMerchantStatus).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByRole('heading', { name: /paytabs urls/i })).toBeTruthy()
    expect(screen.getByText('https://example-student.test/terms')).toBeTruthy()
    expect(screen.getByText('https://example-student.test/privacy')).toBeTruthy()
    expect(screen.queryByText(/teach\./i)).toBeNull()
  })

  it('links to PayTabs docs and refresh reloads status', async () => {
    renderPaymentSetup()

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /going live/i })).toBeTruthy()
    })

    const goingLive = screen.getByRole('link', { name: /going live/i })
    expect(goingLive.getAttribute('href')).toContain('paytabs.com')
    expect(goingLive.getAttribute('target')).toBe('_blank')
    expect(goingLive.getAttribute('rel')).toBe('noopener noreferrer')

    const apiKeys = screen.getByRole('link', { name: /api keys/i })
    expect(apiKeys.getAttribute('href')).toContain('paytabs.com')
    expect(apiKeys.getAttribute('target')).toBe('_blank')
    expect(apiKeys.getAttribute('rel')).toBe('noopener noreferrer')

    expect(screen.getByText(/one-time usd all-access bundle/i)).toBeTruthy()
    expect(screen.getByText(/merchant of record/i)).toBeTruthy()

    billing.getMerchantStatus.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /refresh status/i }))

    await waitFor(() => {
      expect(billing.getMerchantStatus).toHaveBeenCalledTimes(1)
    })
  })

  it('loads bundle price and saves via setBundlePrice', async () => {
    renderPaymentSetup()

    const input = await screen.findByLabelText(/bundle price \(usd\)/i)
    expect(input).toHaveProperty('value', '150.00')

    fireEvent.change(input, { target: { value: '120.00' } })
    fireEvent.click(screen.getByRole('button', { name: /save bundle price/i }))

    await waitFor(() => {
      expect(pricingApi.setBundlePrice).toHaveBeenCalledWith(12000)
    })
    expect(input).toHaveProperty('value', '120.00')
  })

  it('uses RS palette on settled payment setup view (no legacy Tailwind color utilities)', async () => {
    const { container } = renderPaymentSetup()

    await waitFor(() => {
      expect(screen.getByTestId('merchant-payout-status')).toBeTruthy()
    })

    const pageRoot = container.firstElementChild
    expect(pageRoot).toBeTruthy()
    expect(pageRoot!.className).toMatch(/text-rs-ink/)

    const violations = findForbiddenPaletteClasses(collectClassNames(pageRoot!))
    expect(violations).toEqual([])
  })
})
