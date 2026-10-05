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

  it('keeps the four prototype course cards and ignores catalog duration, level, and key skills', async () => {
    listPublishedCourses.mockResolvedValue([
      course({
        id: 'writing',
        title: 'Scientific Writing',
        description: 'Publish with confidence.',
        level: 'Advanced',
        estimatedHours: 8,
        catalogSkills: ['Manuscripts'],
      }),
    ])

    renderAbout()

    expect(await screen.findByRole('heading', { name: 'Scientific Writing' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Research Methodology' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Statistics & SPSS' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Systematic Reviews & Meta-Analysis' })).toBeTruthy()
    expect(screen.getAllByText('Certificate Available')).toHaveLength(4)
    expect(screen.queryByText('Advanced')).toBeNull()
    expect(screen.queryByText('~8 Hours')).toBeNull()
    expect(screen.queryByText('Key skills')).toBeNull()
    expect(screen.queryByText('Manuscripts')).toBeNull()
  })

  it('renders the prototype teaching philosophy heading', async () => {
    renderAbout()

    expect(await screen.findByRole('heading', { name: 'My Teaching Philosophy' })).toBeTruthy()
  })

  it('keeps the prototype four-course and research-team pathway copy', async () => {
    renderAbout()

    expect(await screen.findByText(/Four flagship courses/i)).toBeTruthy()
    expect(screen.getByText(/Four Connected Courses/i)).toBeTruthy()
    expect(screen.getByText(/Graduates of all four courses become eligible/i)).toBeTruthy()
    expect(screen.getByText(/Research Team Pathway/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: /View Full FAQ/i }).getAttribute('href')).toBe('/faq')
  })
})
