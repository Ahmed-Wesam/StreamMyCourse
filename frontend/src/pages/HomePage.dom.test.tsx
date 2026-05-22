/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { FIGMA_MOCK_COURSE_INSTRUCTOR_NAME } from '../lib/figma-mocks.data'

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
    expect(ctas.some((link) => link.getAttribute('href') === '/details#pricing')).toBe(true)
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

  it('shows mock instructor name and WebP hero image', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText(FIGMA_MOCK_COURSE_INSTRUCTOR_NAME).length).toBeGreaterThan(0)

    const instructorImage = screen.getByRole('img', {
      name: FIGMA_MOCK_COURSE_INSTRUCTOR_NAME,
    })
    expect(instructorImage.getAttribute('src') ?? '').toMatch(/\.webp($|\?)/i)
  })
})

