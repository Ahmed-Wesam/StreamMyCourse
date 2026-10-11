/**
 * @vitest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import CheckoutPage from './CheckoutPage'

function renderCheckout(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/billing/result" element={<CheckoutPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CheckoutPage', () => {
  it('says checkout is closed and does not load a card form', async () => {
    renderCheckout('/checkout')
    expect(await screen.findByRole('heading', { name: /Checkout is closed/i })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /pay/i })).toBeNull()
    expect(document.querySelector('form.paymentWidgets')).toBeNull()
  })
})
