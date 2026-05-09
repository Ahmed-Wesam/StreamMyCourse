/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import HomePage from './HomePage'

describe('HomePage', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders hero heading and primary CTA', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', {
        name: /SPSS Spectrum/i,
        level: 1,
      }),
    ).toBeTruthy()

    const ctas = screen.getAllByRole('link', { name: /View Course & Pricing/i })
    expect(ctas.some((link) => link.getAttribute('href') === '/course#pricing')).toBe(true)
  })

  it('renders the instructor section', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { name: /Meet Your Instructor/i }),
    ).toBeTruthy()
  })
})

