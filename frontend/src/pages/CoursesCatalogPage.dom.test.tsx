/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicCatalogCourse } from '../lib/api/public-catalog'

const listPublishedCourses = vi.fn()
const listCourses = vi.fn()

vi.mock('../lib/api/public-catalog', () => ({
  listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
}))

vi.mock('../lib/api/catalog', () => ({
  listCourses: (...args: unknown[]) => listCourses(...args),
}))

import CoursesCatalogPage from './CoursesCatalogPage'

function course(partial: Partial<PublicCatalogCourse> & Pick<PublicCatalogCourse, 'id' | 'title'>): PublicCatalogCourse {
  return {
    description: partial.description ?? `${partial.title} description`,
    ...partial,
  }
}

function renderCatalog() {
  return render(
    <MemoryRouter>
      <CoursesCatalogPage />
    </MemoryRouter>,
  )
}

describe('CoursesCatalogPage', () => {
  beforeEach(() => {
    listPublishedCourses.mockReset()
    listCourses.mockReset()
    listPublishedCourses.mockResolvedValue([])
  })

  afterEach(() => {
    cleanup()
  })

  it('renders hero with Choose Your Learning Path', async () => {
    renderCatalog()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Choose Your Learning Path/i })).toBeTruthy()
    })
  })

  it('shows empty catalog message when there are no published courses', async () => {
    listPublishedCourses.mockResolvedValue([])

    renderCatalog()

    expect(await screen.findByText('Courses will appear here')).toBeTruthy()
    expect(listCourses).not.toHaveBeenCalled()
  })

  it('renders one course with View Course and View Curriculum links', async () => {
    listPublishedCourses.mockResolvedValue([
      course({
        id: 'stats-spss',
        title: 'Statistics & SPSS',
        description: 'Hands-on SPSS training.',
      }),
    ])

    renderCatalog()

    expect(await screen.findByText('Statistics & SPSS')).toBeTruthy()
    expect(screen.getByText('Hands-on SPSS training.')).toBeTruthy()

    const viewCourse = screen.getByRole('link', { name: /^View Course$/i })
    expect(viewCourse.getAttribute('href')).toBe('/courses/stats-spss')

    const viewCurriculum = screen.getByRole('link', { name: /^View Curriculum$/i })
    expect(viewCurriculum.getAttribute('href')).toBe('/courses/stats-spss#curriculum')

    expect(listCourses).not.toHaveBeenCalled()
  })

  it('renders several course titles from the catalog', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'a', title: 'Alpha Methods' }),
      course({ id: 'b', title: 'Beta Statistics' }),
      course({ id: 'c', title: 'Gamma Writing' }),
    ])

    renderCatalog()

    await waitFor(() => {
      expect(screen.getAllByText('Alpha Methods').length).toBeGreaterThan(0)
    })
    expect(screen.getAllByText('Beta Statistics').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gamma Writing').length).toBeGreaterThan(0)
  })

  it('renders no dollar amounts in the document', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'methodology', title: 'Research Methodology' }),
    ])

    const { container } = renderCatalog()

    await waitFor(() => {
      expect(screen.getByText('Research Methodology')).toBeTruthy()
    })

    expect(container.textContent ?? '').not.toMatch(/\$/)
  })

  it('has no Continue Learning or Resume controls', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'c-1', title: 'Course One' }),
    ])

    renderCatalog()

    await waitFor(() => {
      expect(screen.getAllByText('Course One').length).toBeGreaterThan(0)
    })

    expect(screen.queryByRole('link', { name: /Continue Learning/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /Continue Learning/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Continue$/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Resume$/i })).toBeNull()
  })

  it('shows a retryable error and refetches when retry is clicked', async () => {
    listPublishedCourses
      .mockRejectedValueOnce(new Error('Failed to load courses (500)'))
      .mockResolvedValueOnce([course({ id: 'retry-1', title: 'Recovered Course' })])

    renderCatalog()

    expect(await screen.findByText(/Failed to load courses \(500\)/i)).toBeTruthy()
    expect(listPublishedCourses).toHaveBeenCalledTimes(1)
    expect(listCourses).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /retry|try again/i }))

    await waitFor(() => {
      expect(listPublishedCourses).toHaveBeenCalledTimes(2)
    })
    expect((await screen.findAllByText('Recovered Course')).length).toBeGreaterThan(0)
  })
})
