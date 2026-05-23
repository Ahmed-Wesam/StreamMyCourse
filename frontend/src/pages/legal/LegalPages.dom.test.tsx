/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import PrivacyPage from './PrivacyPage'
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
      screen.getByRole('heading', { level: 1, name: /Terms and Conditions/i }),
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
})
