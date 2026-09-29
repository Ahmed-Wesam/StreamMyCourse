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

  it('Privacy describes shipped data types and omits invented certificate visibility controls', () => {
    const { container } = render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    )

    const pageText = container.textContent ?? ''

    expect(pageText).toMatch(/profession/i)
    expect(pageText).toMatch(/purchase/i)
    expect(pageText).toMatch(/lesson notes/i)
    expect(pageText).toMatch(/assignment submission/i)
    expect(pageText).not.toMatch(/Lesson uploads and other course materials you submit/i)
    expect(pageText).not.toMatch(/Examination results/i)
    expect(pageText).not.toMatch(/QR verification data/i)
    expect(pageText).not.toMatch(/Maximum registered device limits/i)
    expect(pageText).not.toMatch(/Learning management systems/i)
    expect(pageText).not.toMatch(/unsubscribe from marketing communications at any time/i)
    expect(pageText).not.toMatch(/• Phone number/i)
    expect(pageText).toMatch(/Research Team application|application PII/i)
    expect(pageText).not.toMatch(/Certificate Visibility Controls/i)
    expect(pageText).not.toMatch(/account deletion through the platform's account settings/i)
    expect(pageText).toMatch(/Contact|support@/i)
  })

  it('Refund still describes one-time purchases without a current subscription model', () => {
    const { container } = render(
      <MemoryRouter>
        <RefundPage />
      </MemoryRouter>,
    )

    const pageText = container.textContent ?? ''
    expect(pageText).toMatch(/does not currently operate on a subscription model/i)
    expect(pageText).toMatch(/no recurring subscription charges/i)
  })
})
