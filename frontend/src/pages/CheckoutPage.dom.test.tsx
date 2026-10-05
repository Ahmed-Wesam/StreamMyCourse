/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const billingApi = vi.hoisted(() => ({
  createCheckoutSession: vi.fn(),
  getBundle: vi.fn(),
  getPurchases: vi.fn(),
}))

const catalogApi = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listPublishedCourses: vi.fn(),
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
    getPurchases: (...args: unknown[]) => billingApi.getPurchases(...args),
  }
})

vi.mock('../lib/api/public-catalog', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/public-catalog')>()
  return {
    ...mod,
    listPublishedCourses: (...args: unknown[]) => catalogApi.listPublishedCourses(...args),
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

const publishedCourses = [
  { id: 'c1', title: 'Research Methodology', description: 'd', amountMinor: 5000 },
  { id: 'c2', title: 'Statistics & SPSS', description: 'd', amountMinor: 5000 },
  { id: 'c3', title: 'Scientific Writing', description: 'd', amountMinor: 5000 },
  { id: 'c4', title: 'Systematic Reviews & Meta-Analysis', description: 'd', amountMinor: 5000 },
]

async function fillCheckoutForm() {
  fireEvent.change(await screen.findByLabelText(/Full Name/i), { target: { value: 'Ada Lovelace' } })
  fireEvent.change(screen.getByLabelText(/^Country/i), { target: { value: 'Jordan' } })
  fireEvent.click(screen.getByLabelText(/Terms & Conditions/i))
  fireEvent.click(screen.getByLabelText(/Privacy Policy/i))
  fireEvent.click(screen.getByLabelText(/Refund Policy/i))
}

describe('CheckoutPage', () => {
  beforeEach(() => {
    billingApi.createCheckoutSession.mockReset()
    billingApi.getBundle.mockReset()
    billingApi.getPurchases.mockReset()
    catalogApi.getCourse.mockReset()
    catalogApi.listPublishedCourses.mockReset()
    sessionApi.hasSignedInIdToken.mockReset()
    sessionApi.hasSignedInIdToken.mockResolvedValue(true)
    billingApi.getBundle.mockResolvedValue({ amountMinor: 15000, currency: 'USD' })
    billingApi.getPurchases.mockResolvedValue([])
    catalogApi.listPublishedCourses.mockResolvedValue(publishedCourses)
  })

  afterEach(() => {
    cleanup()
  })

  it('shows invalid link state when productType is missing', async () => {
    renderCheckout('/checkout')
    expect(await screen.findByText(/invalid/i)).toBeTruthy()
  })

  it('shows prototype checkout hero and no PayTabs wording', async () => {
    renderCheckout('/checkout?productType=bundle')

    expect(await screen.findByText('Secure Checkout')).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Complete Your/i })).toBeTruthy()
    expect(document.body.textContent?.includes('PayTabs')).toBe(false)
  })

  it('loads bundle summary and redirects only via API redirect_url', async () => {
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

    expect(await screen.findByText('$150')).toBeTruthy()
    await fillCheckoutForm()
    fireEvent.click(screen.getByTestId('checkout-submit'))

    await waitFor(() => {
      expect(billingApi.createCheckoutSession).toHaveBeenCalledWith({ productType: 'bundle' })
    })
    expect(hrefSetter).toHaveBeenCalledWith('https://pay.example/session')
  })

  it('prompts sign in when viewer is logged out', async () => {
    sessionApi.hasSignedInIdToken.mockResolvedValue(false)

    renderCheckout('/checkout?productType=bundle')

    expect(await screen.findByRole('button', { name: /Sign in to continue/i })).toBeTruthy()
    expect(screen.queryByTestId('checkout-submit')).toBeNull()
  })

  it('loads course checkout params', async () => {
    catalogApi.getCourse.mockResolvedValue({
      id: 'c2',
      title: 'Statistics & SPSS',
      description: 'd',
      status: 'PUBLISHED',
      amountMinor: 4900,
    })

    renderCheckout('/checkout?productType=course&courseId=c2')

    await waitFor(() => {
      expect(document.querySelector('.hsc-product')?.textContent).toBe('Statistics & SPSS')
      expect(document.querySelector('.os-total-price')?.textContent).toBe('$49')
    })
  })
})
