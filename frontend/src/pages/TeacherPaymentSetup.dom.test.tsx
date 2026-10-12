/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api/client'
import TeacherPaymentSetup from './TeacherPaymentSetup'

const billingApi = vi.hoisted(() => ({
  getBundle: vi.fn(),
}))

const pricingApi = vi.hoisted(() => ({
  setBundlePrice: vi.fn(),
}))

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
    billingApi.getBundle.mockReset()
    billingApi.getBundle.mockResolvedValue({ amountMinor: 150_000, currency: 'JOD' })
    pricingApi.setBundlePrice.mockReset()
    pricingApi.setBundlePrice.mockResolvedValue({ amountMinor: 120_000, currency: 'JOD' })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('shows pricing heading and HyperPay copy without PayTabs checklist', async () => {
    renderPaymentSetup()

    expect(await screen.findByRole('heading', { name: /^Pricing$/i })).toBeTruthy()
    expect(screen.getByText(/HyperPay/i)).toBeTruthy()
    expect(document.body.textContent?.includes('PayTabs')).toBe(false)
    expect(screen.queryByTestId('merchant-payout-status')).toBeNull()
  })

  it('loads bundle price and saves via setBundlePrice (whole JOD)', async () => {
    renderPaymentSetup()

    const input = await screen.findByLabelText(/bundle price \(jod\)/i)
    expect(input).toHaveProperty('value', '150')

    fireEvent.change(input, { target: { value: '120' } })
    fireEvent.click(screen.getByRole('button', { name: /save bundle price/i }))

    await waitFor(() => {
      expect(pricingApi.setBundlePrice).toHaveBeenCalledWith(120_000)
    })
    expect(input).toHaveProperty('value', '120')
  })

  it('shows a permission message when bundle price returns 403', async () => {
    billingApi.getBundle.mockRejectedValue(new ApiError('Forbidden', 403, 'forbidden'))
    renderPaymentSetup()

    await waitFor(() => {
      expect(
        screen.getByText(/only the designated billing teacher can change the bundle price/i),
      ).toBeTruthy()
    })
  })

  it('uses RS palette on settled pricing view (no legacy Tailwind color utilities)', async () => {
    const { container } = renderPaymentSetup()

    await waitFor(() => {
      expect(screen.getByLabelText(/bundle price \(jod\)/i)).toBeTruthy()
    })

    const pageRoot = container.firstElementChild
    expect(pageRoot).toBeTruthy()
    expect(pageRoot!.className).toMatch(/text-rs-ink/)

    const violations = findForbiddenPaletteClasses(collectClassNames(pageRoot!))
    expect(violations).toEqual([])
  })
})
