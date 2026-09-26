/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicCatalogCourse } from '../lib/api/public-catalog'

const listPublishedCourses = vi.fn()

vi.mock('../lib/api/public-catalog', () => ({
  listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
}))

import HomePage from './HomePage'

const COURSES_HEADING = 'Four Courses. One Complete Research Skill Set.'

function course(partial: Partial<PublicCatalogCourse> & Pick<PublicCatalogCourse, 'id' | 'title'>): PublicCatalogCourse {
  return {
    description: partial.description ?? `${partial.title} description`,
    ...partial,
  }
}

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    listPublishedCourses.mockReset()
    listPublishedCourses.mockResolvedValue([])
  })

  afterEach(() => {
    cleanup()
  })

  it('renders hero copy with Publish With Confidence', async () => {
    renderHome()

    await waitFor(() => {
      expect(screen.getByText(/Publish With Confidence/i)).toBeTruthy()
    })
  })

  it.each([1, 2] as const)(
    'keeps literal courses heading when catalog returns %i course(s)',
    async (count) => {
      const courses = Array.from({ length: count }, (_, i) =>
        course({ id: `c${i + 1}`, title: `Course ${i + 1}` }),
      )
      listPublishedCourses.mockResolvedValue(courses)

      renderHome()

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { name: COURSES_HEADING }),
        ).toBeTruthy()
      })
      expect(screen.getAllByText(courses[0]!.title).length).toBeGreaterThan(0)
    },
  )

  it('hero primary CTA links to /courses and has no View Course & Pricing CTA', async () => {
    renderHome()

    await waitFor(() => {
      expect(screen.getByText(/Publish With Confidence/i)).toBeTruthy()
    })

    const exploreLinks = screen.getAllByRole('link', { name: /Explore courses/i })
    expect(exploreLinks.some((link) => link.getAttribute('href') === '/courses')).toBe(true)

    expect(screen.queryByRole('link', { name: /View Course & Pricing/i })).toBeNull()
  })

  it('renders no dollar amounts in the document', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'methodology', title: 'Research Methodology' }),
    ])

    const { container } = renderHome()

    await waitFor(() => {
      expect(screen.getAllByText('Research Methodology').length).toBeGreaterThan(0)
    })

    expect(container.textContent ?? '').not.toMatch(/\$/)
  })

  it('shows empty catalog message when there are no published courses', async () => {
    listPublishedCourses.mockResolvedValue([])

    renderHome()

    expect(await screen.findByText('Courses will appear here')).toBeTruthy()
  })

  it('renders one course title and a View Course link to /courses/:id', async () => {
    listPublishedCourses.mockResolvedValue([
      course({
        id: 'stats-spss',
        title: 'Statistics & SPSS',
        description: 'Hands-on SPSS training.',
      }),
    ])

    renderHome()

    expect((await screen.findAllByText('Statistics & SPSS')).length).toBeGreaterThan(0)
    expect(screen.getByText('Hands-on SPSS training.')).toBeTruthy()

    const viewLink = screen.getByRole('link', { name: /View Course/i })
    expect(viewLink.getAttribute('href')).toBe('/courses/stats-spss')
  })

  it('renders several course titles as cards and bundle chips', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'a', title: 'Alpha Methods' }),
      course({ id: 'b', title: 'Beta Statistics' }),
      course({ id: 'c', title: 'Gamma Writing' }),
    ])

    renderHome()

    await waitFor(() => {
      expect(screen.getAllByText('Alpha Methods').length).toBeGreaterThanOrEqual(2)
    })

    for (const title of ['Alpha Methods', 'Beta Statistics', 'Gamma Writing']) {
      expect(screen.getAllByText(title).length).toBeGreaterThanOrEqual(2)
    }

    const coursesSection = document.getElementById('courses')
    expect(coursesSection).toBeTruthy()
    const exploreInCourses = within(coursesSection!).getAllByRole('link', {
      name: /^Explore courses$/i,
    })
    expect(exploreInCourses.length).toBeGreaterThan(0)
    expect(exploreInCourses.every((link) => link.getAttribute('href') === '/courses')).toBe(true)
  })

  it('shows a retryable error and refetches when retry is clicked', async () => {
    listPublishedCourses
      .mockRejectedValueOnce(new Error('Failed to load courses (500)'))
      .mockResolvedValueOnce([course({ id: 'retry-1', title: 'Recovered Course' })])

    renderHome()

    expect(await screen.findByText(/Failed to load courses \(500\)/i)).toBeTruthy()
    expect(listPublishedCourses).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: /retry|try again/i }))

    await waitFor(() => {
      expect(listPublishedCourses).toHaveBeenCalledTimes(2)
    })
    expect((await screen.findAllByText('Recovered Course')).length).toBeGreaterThan(0)
  })
})
