/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { BRAND_NAME, BRAND_TAGLINE, FOOTER_BLURB } from '../../lib/brand'
import { Footer } from './Footer'

describe('Footer', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders Platform, Legal, and Account headings with brand copy', () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Platform' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Legal' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Account' })).toBeTruthy()
    expect(screen.getByText(BRAND_NAME, { exact: false })).toBeTruthy()
    expect(screen.getByText(FOOTER_BLURB)).toBeTruthy()
    expect(screen.getByText(BRAND_TAGLINE, { exact: false })).toBeTruthy()
  })

  it('uses relative legal links when legalBaseUrl is unset', () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Privacy Policy' }).getAttribute('href')).toBe(
      '/privacy',
    )
  })

  it('uses absolute Platform and Legal links when legalBaseUrl is set', () => {
    render(
      <MemoryRouter>
        <Footer legalBaseUrl="https://researchspectrum.org" />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Privacy Policy' }).getAttribute('href')).toBe(
      'https://researchspectrum.org/privacy',
    )
    expect(screen.getByRole('link', { name: 'Courses' }).getAttribute('href')).toBe(
      'https://researchspectrum.org/courses',
    )
  })

  it('prototype variant uses prototype footer markup', () => {
    const { container } = render(
      <MemoryRouter>
        <Footer variant="prototype" />
      </MemoryRouter>,
    )

    const footer = container.querySelector('footer')
    expect(footer?.querySelector('.wrap .foot-grid')).toBeTruthy()
    expect(footer?.querySelector('a.logo img.mark')).toBeTruthy()
    expect(footer?.querySelector('.foot-bottom .foot-social')).toBeTruthy()
    expect(footer?.querySelector('.rs-foot-social')).toBeNull()
    expect(footer?.className ?? '').not.toMatch(/\bborder-t\b/)
    expect(screen.getByRole('link', { name: 'Privacy Policy' }).getAttribute('href')).toBe('/privacy')
    const year = new Date().getFullYear()
    expect(
      screen.getByText(`© ${year} ${BRAND_NAME}. ${BRAND_TAGLINE}.`),
    ).toBeTruthy()
  })

  it('exposes Instagram with noopener and an accessible name', () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )

    const instagram = screen.getByRole('link', { name: 'Instagram' })
    expect(instagram.getAttribute('rel') ?? '').toMatch(/noopener/)
  })
})
