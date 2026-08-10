/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import DeliveryPage from './DeliveryPage'
import EducationalDisclaimerPage from './EducationalDisclaimerPage'
import PrivacyPage from './PrivacyPage'
import RefundPage from './RefundPage'
import TermsPage from './TermsPage'

describe('Legal pages', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders Terms page with English title', () => {
    render(
      <MemoryRouter>
        <TermsPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { level: 1, name: /Terms & Conditions/i }),
    ).toBeTruthy()
  })

  it('shows Arabic title and rtl prose on Terms when Arabic toggle is selected', () => {
    render(
      <MemoryRouter>
        <TermsPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /Arabic/i }))

    expect(
      screen.getByRole('heading', { level: 1, name: /الشروط والأحكام/i }),
    ).toBeTruthy()

    const prose = screen.getByTestId('legal-prose')
    expect(prose.getAttribute('dir')).toBe('rtl')
  })

  it('renders Privacy page with English title', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: /Privacy Policy/i })).toBeTruthy()
  })

  it('shows Arabic title and rtl prose on Privacy when Arabic toggle is selected', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /Arabic/i }))

    expect(screen.getByRole('heading', { level: 1, name: /سياسة الخصوصية/i })).toBeTruthy()

    const prose = screen.getByTestId('legal-prose')
    expect(prose.getAttribute('dir')).toBe('rtl')
  })

  it('renders Refund page with English title', () => {
    render(
      <MemoryRouter>
        <RefundPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { level: 1, name: /Refund & Cancellation Policy/i }),
    ).toBeTruthy()
  })

  it('renders Delivery page with English title', () => {
    render(
      <MemoryRouter>
        <DeliveryPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: /Delivery Policy/i })).toBeTruthy()
  })

  it('renders Educational Disclaimer page with English title', () => {
    render(
      <MemoryRouter>
        <EducationalDisclaimerPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: /Educational Disclaimer/i })).toBeTruthy()
  })
})
