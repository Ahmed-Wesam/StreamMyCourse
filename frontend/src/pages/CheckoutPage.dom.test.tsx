/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const billingApi = vi.hoisted(() => ({
  createCheckoutSession: vi.fn(),
  getBundle: vi.fn(),
}))

const catalogApi = vi.hoisted(() => ({
  getCourse: vi.fn(),
}))

const sessionApi = vi.hoisted(() => ({
  hasSignedInIdToken: vi.fn(),
}))

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/billing')>()
  return {
    ...mod,
    createCheckoutSession: (...args: unknown[]) => billingApi.createCheckoutSession(...args),
    getBundle: (...args: unknown[]) => billingApi.getBundle(...args),
  }
})

vi.mock('../lib/api/catalog', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/catalog')>()
  return {
    ...mod,
    getCourse: (...args: unknown[]) => catalogApi.getCourse(...args),
  }
})

vi.mock('../lib/api/session', () => ({
  hasSignedInIdToken: () => sessionApi.hasSignedInIdToken(),
}))

import CheckoutPage from './CheckoutPage'

function renderCheckout(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/login" element={<div data-testid="login-page" />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CheckoutPage', () => {
  beforeEach(() => {
    billingApi.createCheckoutSession.mockReset()
    billingApi.getBundle.mockReset()
    catalogApi.getCourse.mockReset()
    sessionApi.hasSignedInIdToken.mockReset()
    sessionApi.hasSignedInIdToken.mockResolvedValue(true)
  })

  afterEach(() => {
    cleanup()
  })

  it('shows invalid link state when productType is missing', async () => {
    renderCheckout('/checkout')
    expect(await screen.findByText(/invalid/i)).toBeTruthy()
  })

  it('loads bundle summary and redirects only via API redirect_url', async () => {
    billingApi.getBundle.mockResolvedValue({ amountMinor: 15000, currency: 'USD' })
    billingApi.createCheckoutSession.mockResolvedValue({ redirect_url: 'https://pay.example/session' })

    const hrefSetter = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        ...window.location,
        set href(v: string) {
          hrefSetter(v)
        },
        get href() {
          return ''
        },
      },
    })

    renderCheckout('/checkout?productType=bundle')

    expect(await screen.findByText('$150.00')).toBeTruthy()
    fireEvent.click(screen.getByTestId('checkout-submit'))

    await waitFor(() => {
      expect(billingApi.createCheckoutSession).toHaveBeenCalledWith({ productType: 'bundle' })
    })
    expect(hrefSetter).toHaveBeenCalledWith('https://pay.example/session')
  })

  it('prompts sign in when viewer is logged out', async () => {
    sessionApi.hasSignedInIdToken.mockResolvedValue(false)
    billingApi.getBundle.mockResolvedValue({ amountMinor: 15000, currency: 'USD' })

    renderCheckout('/checkout?productType=bundle')

    expect(await screen.findByRole('button', { name: /Sign in to continue/i })).toBeTruthy()
    expect(screen.queryByTestId('checkout-submit')).toBeNull()
  })

  it('loads course checkout params', async () => {
    catalogApi.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Statistics & SPSS',
      description: 'd',
      status: 'PUBLISHED',
      amountMinor: 4900,
    })

    renderCheckout('/checkout?productType=course&courseId=c1')

    expect(await screen.findByText('Statistics & SPSS')).toBeTruthy()
    expect(await screen.findByText('$49.00')).toBeTruthy()
  })
})
