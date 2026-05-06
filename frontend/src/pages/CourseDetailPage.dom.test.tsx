/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CourseDetailPage from './CourseDetailPage'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listLessons: vi.fn(),
  getCourseProgress: vi.fn(),
  hasSignedInIdToken: vi.fn(),
  enrollInCourse: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    getCourse: (...args: unknown[]) => api.getCourse(...args) as ReturnType<typeof mod.getCourse>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
    hasSignedInIdToken: (...args: unknown[]) =>
      api.hasSignedInIdToken(...args) as ReturnType<typeof mod.hasSignedInIdToken>,
    enrollInCourse: (...args: unknown[]) =>
      api.enrollInCourse(...args) as ReturnType<typeof mod.enrollInCourse>,
  }
})

function renderCourseDetail(path = '/courses/c1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/courses/:courseId" element={<CourseDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CourseDetailPage', () => {
  beforeEach(() => {
    api.getCourse.mockReset()
    api.listLessons.mockReset()
    api.getCourseProgress.mockReset()
    api.hasSignedInIdToken.mockReset()
    api.enrollInCourse.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })
    api.listLessons.mockResolvedValue([
      { id: 'l1', title: 'First Lesson', order: 1, videoStatus: 'ready', duration: 100 },
      { id: 'l2', title: 'Second Lesson', order: 2, videoStatus: 'ready', duration: 200 },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 0,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 0 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })
    api.hasSignedInIdToken.mockResolvedValue(true)
    api.enrollInCourse.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders course title', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Test Course')).toBeTruthy()
    })
  })

  it('renders list of lessons', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.getByText('Second Lesson')).toBeTruthy()
  })

  it('shows Start Learning button for new course', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Start Learning')).toBeTruthy()
    })
  })

  it('shows Resume Learning button when progress exists', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 25,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 50 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Resume Learning')).toBeTruthy()
    })
  })

  it('shows Enroll button when not enrolled', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: false,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Enroll for free')).toBeTruthy()
    })
  })

  it('calls enrollInCourse when Enroll button clicked', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: false,
    })

    renderCourseDetail()

    const enrollButton = await waitFor(() => screen.getByText('Enroll for free'))
    fireEvent.click(enrollButton)

    await waitFor(() => {
      expect(api.enrollInCourse).toHaveBeenCalledWith('c1')
    })
  })

  it('shows Sign in prompt for anonymous users', async () => {
    api.hasSignedInIdToken.mockResolvedValue(false)

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeTruthy()
    })
  })

  it('links to first lesson when Start Learning clicked', async () => {
    renderCourseDetail()

    const startButton = await waitFor(() => screen.getByText('Start Learning'))
    const href = startButton.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/lessons/l1')
  })

  it('links to lesson with resume time when Resume Learning clicked', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 25,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 50 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    const resumeButton = await waitFor(() => screen.getByText('Resume Learning'))
    const href = resumeButton.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/lessons/l1?t=50')
  })

  it('shows lesson thumbnails with progress bars', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 30 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      const progressBars = screen.getAllByRole('progressbar')
      expect(progressBars.length).toBeGreaterThan(0)
    })
  })

  it('shows loading state initially', () => {
    renderCourseDetail()
    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('shows error message when course fails to load', async () => {
    api.getCourse.mockRejectedValue(new Error('Failed to fetch'))

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch/i)).toBeTruthy()
    })
  })

  it('shows No lessons message when course has no lessons', async () => {
    api.listLessons.mockResolvedValue([])

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/No lessons yet/i)).toBeTruthy()
    })
  })

  it('links back to all courses', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Back to all courses')).toBeTruthy()
    })
  })
})
