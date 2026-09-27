/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import BillingCancelPage from './BillingCancelPage'
import BillingSuccessPage from './BillingSuccessPage'
import {
  billingCancelMessage,
  billingSuccessMessage,
} from '../lib/purchaseCopy'

function renderBillingRoute(path: '/billing/success' | '/billing/cancel') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/billing/success" element={<BillingSuccessPage />} />
        <Route path="/billing/cancel" element={<BillingCancelPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Billing return pages', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows success copy without granting access client-side', () => {
    const { container } = renderBillingRoute('/billing/success')
    expect(container.firstElementChild?.className).toMatch(/text-rs-ink/)
    expect(screen.getByRole('heading', { name: /Payment received/i })).toBeTruthy()
    expect(screen.getByText(billingSuccessMessage)).toBeTruthy()
    expect(screen.queryByText(/access granted/i)).toBeNull()
    expect(screen.getByRole('link', { name: /Browse courses/i }).getAttribute('href')).toBe('/courses')
  })

  it('shows cancel copy and link back to courses', () => {
    const { container } = renderBillingRoute('/billing/cancel')
    expect(container.firstElementChild?.className).toMatch(/text-rs-ink/)
    expect(screen.getByRole('heading', { name: /Checkout canceled/i })).toBeTruthy()
    expect(screen.getByText(billingCancelMessage)).toBeTruthy()
    expect(screen.getByRole('link', { name: /Browse courses/i }).getAttribute('href')).toBe('/courses')
  })
})
