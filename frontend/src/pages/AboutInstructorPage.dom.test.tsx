/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicCatalogCourse } from '../lib/api/public-catalog'

const listPublishedCourses = vi.fn()

vi.mock('../lib/api/public-catalog', () => ({
  listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
}))

import AboutInstructorPage from './AboutInstructorPage'

function course(
  partial: Partial<PublicCatalogCourse> & Pick<PublicCatalogCourse, 'id' | 'title'>,
): PublicCatalogCourse {
  return {
    description: partial.description ?? `${partial.title} description`,
    ...partial,
  }
}

function renderAbout() {
  return render(
    <MemoryRouter>
      <AboutInstructorPage />
    </MemoryRouter>,
  )
}

describe('AboutInstructorPage', () => {
  beforeEach(() => {
    listPublishedCourses.mockReset()
    listPublishedCourses.mockResolvedValue([])
  })

  afterEach(() => {
    cleanup()
  })

  it('shows instructor name, photo, a DOI publication link, and a mocked course title without dollar amounts', async () => {
    listPublishedCourses.mockResolvedValue([
      course({
        id: 'methodology',
        title: 'Research Methodology',
        description: 'Design rigorous research studies.',
      }),
    ])

    const { container } = renderAbout()

    expect((await screen.findAllByText('Dr. Bahaa Aburayya')).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('img', { name: 'Dr. Bahaa Aburayya' }).length).toBeGreaterThan(0)

    const doiLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') ?? '').startsWith('https://doi.org/'))
    expect(doiLinks.length).toBeGreaterThan(0)
    expect(doiLinks.some((link) => (link.getAttribute('rel') ?? '').includes('noopener'))).toBe(
      true,
    )

    expect(await screen.findByText('Research Methodology')).toBeTruthy()

    expect(container.textContent ?? '').not.toMatch(/\$/)
  })
})
