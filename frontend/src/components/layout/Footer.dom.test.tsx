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
