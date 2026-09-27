/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { AccountLayout } from './AccountLayout'

describe('AccountLayout', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders sidebar links for Profile and My purchases', () => {
    render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<div>Profile content</div>} />
            <Route path="purchases" element={<div>Purchases content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    const nav = screen.getByRole('navigation', { name: /account/i })
    expect(nav).toBeTruthy()

    const profile = screen.getByRole('link', { name: 'Profile' })
    expect(profile.getAttribute('href')).toBe('/account/profile')

    const purchases = screen.getByRole('link', { name: 'My purchases' })
    expect(purchases.getAttribute('href')).toBe('/account/purchases')
  })

  it('layout root uses text-rs-ink', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<div>Profile content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(container.firstElementChild?.className).toMatch(/text-rs-ink/)
  })
})
