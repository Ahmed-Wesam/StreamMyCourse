/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import type { ComponentType } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import DeliveryPage from './DeliveryPage'
import EducationalDisclaimerPage from './EducationalDisclaimerPage'
import PrivacyPage from './PrivacyPage'
import RefundPage from './RefundPage'
import TermsPage from './TermsPage'

const legalPages: Array<{ name: string; Page: ComponentType; title: RegExp }> = [
  { name: 'Terms', Page: TermsPage, title: /Terms & Conditions/i },
  { name: 'Privacy', Page: PrivacyPage, title: /Privacy Policy/i },
  {
    name: 'Refund',
    Page: RefundPage,
    title: /Refund & Cancellation Policy/i,
  },
  { name: 'Delivery', Page: DeliveryPage, title: /Delivery Policy/i },
  {
    name: 'Educational Disclaimer',
    Page: EducationalDisclaimerPage,
    title: /Educational Disclaimer/i,
  },
]

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

  it('renders Privacy page with English title', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: /Privacy Policy/i })).toBeTruthy()
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

  it.each(legalPages)('$name page root uses text-rs-ink', ({ Page, title }) => {
    const { container } = render(
      <MemoryRouter>
        <Page />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: title })).toBeTruthy()
    expect(container.firstElementChild?.className).toMatch(/text-rs-ink/)
  })
})
