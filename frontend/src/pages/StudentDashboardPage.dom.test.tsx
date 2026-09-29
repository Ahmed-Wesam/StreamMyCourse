/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getPurchases = vi.fn()
const listPublishedCourses = vi.fn()
const fetchMe = vi.fn()
const getCourseProgress = vi.fn()
const listLessons = vi.fn()
const listCourseModules = vi.fn()
const listMyCertificates = vi.fn()

vi.mock('../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/billing')>()
  return {
    ...mod,
    getPurchases: (...args: unknown[]) => getPurchases(...args),
  }
})

vi.mock('../lib/api/public-catalog', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/public-catalog')>()
  return {
    ...mod,
    listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
  }
})

vi.mock('../lib/api/session', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/session')>()
  return {
    ...mod,
    fetchMe: (...args: unknown[]) => fetchMe(...args),
  }
})

vi.mock('../lib/api/catalog', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/catalog')>()
  return {
    ...mod,
    getCourseProgress: (...args: unknown[]) => getCourseProgress(...args),
    listLessons: (...args: unknown[]) => listLessons(...args),
    listCourseModules: (...args: unknown[]) => listCourseModules(...args),
  }
})

vi.mock('../lib/api/certificates', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/certificates')>()
  return {
    ...mod,
    listMyCertificates: (...args: unknown[]) => listMyCertificates(...args),
  }
})

import StudentDashboardPage from './StudentDashboardPage'

function renderDashboard() {
  return render(
    <MemoryRouter>
      <StudentDashboardPage />
    </MemoryRouter>,
  )
}

describe('StudentDashboardPage', () => {
  beforeEach(() => {
    getPurchases.mockReset()
    listPublishedCourses.mockReset()
    fetchMe.mockReset()
    getCourseProgress.mockReset()
    listLessons.mockReset()
    listCourseModules.mockReset()
    listMyCertificates.mockReset()

    listPublishedCourses.mockResolvedValue([
      { id: 'c1', title: 'Alpha Course', description: 'Desc' },
      { id: 'c2', title: 'Beta Course', description: 'Desc' },
    ])
    getPurchases.mockResolvedValue([
      {
        id: 'p1',
        productType: 'course',
        status: 'paid',
        courseId: 'c1',
        amountMinor: 1000,
        currency: 'usd',
        createdAt: '2026-01-01T00:00:00Z',
      },
    ])
    fetchMe.mockResolvedValue({
      userId: 'u1',
      email: 'ada@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
      givenName: 'Ada',
    })
    listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'First lesson',
        order: 0,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Module 1', description: '', order: 0 }])
    getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l1', completed: false, lastPositionSec: 0 }],
    })
    listMyCertificates.mockResolvedValue({
      certificates: [],
      inProgress: [],
      profileIncomplete: [],
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders dashboard root test id', async () => {
    renderDashboard()
    expect(await screen.findByTestId('student-page-dashboard')).toBeTruthy()
  })

  it('shows personalized welcome when profile loads', async () => {
    renderDashboard()
    expect(await screen.findByText(/Welcome back, Ada/i)).toBeTruthy()
  })

  it('shows generic welcome when profile fetch fails', async () => {
    fetchMe.mockRejectedValue(new Error('network'))
    renderDashboard()
    expect(await screen.findByText(/^Welcome back$/i)).toBeTruthy()
  })

  it('shows empty continue state with link to catalog when no owned courses', async () => {
    getPurchases.mockResolvedValue([])
    renderDashboard()
    expect(await screen.findByTestId('student-dashboard-empty')).toBeTruthy()
    expect(screen.getByRole('link', { name: /Browse courses/i }).getAttribute('href')).toBe('/courses')
  })

  it('shows continue card for owned course with lesson link', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('student-dashboard-course-c1')).toBeTruthy()
    })
    expect(screen.getByText('Alpha Course')).toBeTruthy()
    const continueLink = screen.getByRole('link', { name: /Continue/i })
    expect(continueLink.getAttribute('href')).toBe('/courses/c1/lessons/l1')
  })

  it('shows aggregate stats when course data loads', async () => {
    getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })
    listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'L1',
        order: 0,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'L2',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('student-dashboard-stats')).toBeTruthy()
    })
    expect(screen.getByText('50%')).toBeTruthy()
    expect(screen.getByText('1')).toBeTruthy()
  })

  it('shows retry UI when catalog fetch fails and no course cards', async () => {
    listPublishedCourses.mockRejectedValue(new Error('catalog down'))
    renderDashboard()
    expect(await screen.findByTestId('student-dashboard-error')).toBeTruthy()
    expect(screen.queryByTestId('student-dashboard-course-c1')).toBeNull()
    listPublishedCourses.mockResolvedValue([
      { id: 'c1', title: 'Alpha Course', description: 'Desc' },
    ])
    fireEvent.click(screen.getByRole('button', { name: /Try again/i }))
    await waitFor(() => {
      expect(screen.getByTestId('student-dashboard-course-c1')).toBeTruthy()
    })
  })

  it('shows retry UI when purchases fetch fails', async () => {
    getPurchases.mockRejectedValue(new Error('billing down'))
    renderDashboard()
    expect(await screen.findByTestId('student-dashboard-error')).toBeTruthy()
    expect(screen.queryByTestId('student-dashboard-course-c1')).toBeNull()
  })

  it('shows unavailable progress on per-course load failure', async () => {
    getCourseProgress.mockRejectedValue(new Error('progress failed'))
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('student-dashboard-course-c1')).toBeTruthy()
    })
    expect(screen.getByText(/Progress unavailable/i)).toBeTruthy()
  })

  it('counts non-revoked certificates and links to /certificates', async () => {
    listMyCertificates.mockResolvedValue({
      certificates: [
        {
          id: 'cert-1',
          credentialId: 'RS-AAAAAA-2026-ABCDEF1234',
          status: 'valid',
          studentName: 'Ada Lovelace',
          courseTitle: 'Alpha Course',
          issueDate: 'September 2026',
          instructorName: 'Research Spectrum',
          instructorTitle: 'Instructor',
          courseId: 'c1',
        },
        {
          id: 'cert-2',
          credentialId: 'RS-BBBBBB-2026-ABCDEF1234',
          status: 'revoked',
          studentName: 'Ada Lovelace',
          courseTitle: 'Beta Course',
          issueDate: 'August 2026',
          instructorName: 'Research Spectrum',
          instructorTitle: 'Instructor',
          courseId: 'c2',
        },
        {
          id: 'cert-3',
          credentialId: 'RS-CCCCCC-2026-ABCDEF1234',
          status: 'valid',
          studentName: 'Ada Lovelace',
          courseTitle: 'Alpha Course',
          issueDate: 'July 2026',
          instructorName: 'Research Spectrum',
          instructorTitle: 'Instructor',
          courseId: 'c1',
        },
      ],
      inProgress: [],
      profileIncomplete: [],
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('student-dashboard-stats')).toBeTruthy()
    })
    const certLink = screen.getByRole('link', { name: /Certificates/i })
    expect(certLink.getAttribute('href')).toBe('/certificates')
    expect(certLink.textContent).toMatch(/2/)
    expect(certLink.textContent).not.toMatch(/3/)
  })
})
