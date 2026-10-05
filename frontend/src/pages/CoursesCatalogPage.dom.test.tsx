/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicCatalogCourse } from '../lib/api/public-catalog'

const listPublishedCourses = vi.fn()
const listCourses = vi.fn()
const getBundle = vi.fn()
const getPurchases = vi.fn()

vi.mock('../lib/api/public-catalog', () => ({
  listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
}))

vi.mock('../lib/api/catalog', () => ({
  listCourses: (...args: unknown[]) => listCourses(...args),
}))

vi.mock('../lib/api/billing', () => ({
  getBundle: (...args: unknown[]) => getBundle(...args),
  getPurchases: (...args: unknown[]) => getPurchases(...args),
}))

vi.mock('../lib/api/session', () => ({
  hasSignedInIdToken: vi.fn().mockResolvedValue(false),
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
    getBundle.mockReset()
    getPurchases.mockReset()
    listPublishedCourses.mockResolvedValue([])
    getBundle.mockResolvedValue({ amountMinor: 150_000, currency: 'JOD' })
    getPurchases.mockResolvedValue([])
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

  it('shows catalog card meta (level, hours, key skills) when present', async () => {
    listPublishedCourses.mockResolvedValue([
      course({
        id: 'stats-spss',
        title: 'Statistics & SPSS',
        description: 'Hands-on SPSS training.',
        level: 'Intermediate',
        estimatedHours: 18,
        catalogSkills: ['Regression modeling', 'Hypothesis testing'],
      }),
    ])

    renderCatalog()

    expect((await screen.findAllByText('Statistics & SPSS')).length).toBeGreaterThan(0)
    expect(screen.getByText('Duration')).toBeTruthy()
    expect(screen.getByText('Level')).toBeTruthy()
    expect(screen.getByText('Intermediate')).toBeTruthy()
    expect(screen.getByText('~18 Hours')).toBeTruthy()
    expect(screen.getByText('Key skills learned')).toBeTruthy()
    expect(screen.getByText('Regression modeling')).toBeTruthy()
    expect(screen.getByText('Hypothesis testing')).toBeTruthy()
    expect(screen.queryByText(/^one-time$/)).toBeNull()
    expect(screen.getAllByText('one-time payment').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { level: 2, name: 'Compare Courses' })).toBeTruthy()
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

    expect((await screen.findAllByText('Statistics & SPSS')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Hands-on SPSS training.')).toBeTruthy()

    const viewCourse = screen.getByRole('link', { name: /^View Course$/i })
    expect(viewCourse.getAttribute('href')).toBe('/courses/stats-spss')

    const viewCurriculum = screen.getByRole('link', { name: /^View Curriculum$/i })
    expect(viewCurriculum.getAttribute('href')).toBe('/courses/stats-spss#curriculum')

    expect(listCourses).not.toHaveBeenCalled()
  })

  it('renders the four catalog titles in prototype order and hides other published courses', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'stray', title: 'integration-test-published-course' }),
      course({ id: 'writing', title: 'Scientific Writing', amountMinor: 50_000 }),
      course({ id: 'sr', title: 'Systematic Reviews & Meta-Analysis', amountMinor: 50_000 }),
      course({ id: 'stats', title: 'Statistics & SPSS', amountMinor: 50_000 }),
      course({ id: 'method', title: 'Research Methodology', amountMinor: 50_000 }),
    ])

    renderCatalog()

    await waitFor(() => {
      expect(screen.getAllByText('Research Methodology').length).toBeGreaterThan(0)
      expect(screen.queryByText(/integration-test-published-course/i)).toBeNull()
      expect(screen.getAllByText('one-time')).toHaveLength(4)
      expect(screen.getAllByText('one-time payment').length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Save .*50/).length).toBeGreaterThan(0)
    })

    const cardTitles = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
    expect(cardTitles).toEqual([
      'Research Methodology',
      'Statistics & SPSS',
      'Scientific Writing',
      'Systematic Reviews & Meta-Analysis',
      'Research Mastery Bundle',
    ])
  })

  it('shows course and bundle JOD prices from API', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'methodology', title: 'Research Methodology', amountMinor: 99_000 }),
    ])

    renderCatalog()

    expect((await screen.findAllByText('Research Methodology')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/99/)).length).toBeGreaterThan(0)
    await waitFor(() => {
      expect(screen.getAllByText(/150/).length).toBeGreaterThan(0)
    })
  })

  it('has no Continue Learning or Resume controls', async () => {
    listPublishedCourses.mockResolvedValue([
      course({ id: 'c-1', title: 'Research Methodology' }),
    ])

    renderCatalog()

    await waitFor(() => {
      expect(screen.getAllByText('Research Methodology').length).toBeGreaterThan(0)
    })

    expect(screen.queryByRole('link', { name: /Continue Learning/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /Continue Learning/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Continue$/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Resume$/i })).toBeNull()
  })

  it('shows a retryable error and refetches when retry is clicked', async () => {
    listPublishedCourses
      .mockRejectedValueOnce(new Error('Failed to load courses (500)'))
      .mockResolvedValueOnce([course({ id: 'retry-1', title: 'Scientific Writing' })])

    renderCatalog()

    expect(await screen.findByText(/Failed to load courses \(500\)/i)).toBeTruthy()
    expect(listPublishedCourses).toHaveBeenCalledTimes(1)
    expect(listCourses).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /retry|try again/i }))

    await waitFor(() => {
      expect(listPublishedCourses).toHaveBeenCalledTimes(2)
    })
    expect((await screen.findAllByText('Scientific Writing')).length).toBeGreaterThan(0)
  })
})
