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

  it('renders sidebar links for Profile and Manage subscription', () => {
    render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<div>Profile content</div>} />
            <Route path="subscription" element={<div>Subscription content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    const nav = screen.getByRole('navigation', { name: /account/i })
    expect(nav).toBeTruthy()

    const profile = screen.getByRole('link', { name: 'Profile' })
    expect(profile.getAttribute('href')).toBe('/account/profile')

    const subscription = screen.getByRole('link', { name: 'Manage subscription' })
    expect(subscription.getAttribute('href')).toBe('/account/subscription')
  })
})
