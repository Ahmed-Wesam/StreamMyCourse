/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import CourseDetailPage from './CourseDetailPage'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listLessons: vi.fn(),
  listCourseModules: vi.fn(),
  getCourseProgress: vi.fn(),
  hasSignedInIdToken: vi.fn(),
  enrollInCourse: vi.fn(),
  updateLessonProgress: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    getCourse: (...args: unknown[]) => api.getCourse(...args) as ReturnType<typeof mod.getCourse>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    listCourseModules: (...args: unknown[]) =>
      api.listCourseModules(...args) as ReturnType<typeof mod.listCourseModules>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
    hasSignedInIdToken: (...args: unknown[]) =>
      api.hasSignedInIdToken(...args) as ReturnType<typeof mod.hasSignedInIdToken>,
    enrollInCourse: (...args: unknown[]) =>
      api.enrollInCourse(...args) as ReturnType<typeof mod.enrollInCourse>,
    updateLessonProgress: (...args: unknown[]) =>
      api.updateLessonProgress(...args) as ReturnType<typeof mod.updateLessonProgress>,
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
    api.listCourseModules.mockReset()
    api.getCourseProgress.mockReset()
    api.hasSignedInIdToken.mockReset()
    api.enrollInCourse.mockReset()
    api.updateLessonProgress.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'First Lesson',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'Second Lesson',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 200,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
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
    api.updateLessonProgress.mockResolvedValue({
      ok: true,
      lessonProgress: { lessonId: 'l1', completed: true, lastPositionSec: 0 },
    })
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

  it('groups lessons by module and shows module titles', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Section 1')).toBeTruthy()
    })
    expect(screen.getByText('Section 2')).toBeTruthy()
    expect(screen.getByText('First Lesson')).toBeTruthy()
    expect(screen.getByText('Second Lesson')).toBeTruthy()
  })

  it('renders orphan moduleId lessons under an Unsorted section', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'In Module One',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'In Module Two',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 200,
      },
      {
        id: 'l3',
        title: 'Orphan Lesson',
        order: 1,
        moduleId: 'm-unknown',
        moduleOrder: 2,
        videoStatus: 'ready',
        duration: 150,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 3,
      completedCount: 0,
      percentComplete: 0,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 0 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        { lessonId: 'l3', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('In Module One')).toBeTruthy()
    })
    expect(screen.getByText('In Module Two')).toBeTruthy()
    expect(screen.getByText('Orphan Lesson')).toBeTruthy()
    const unsortedHeadings = screen.getAllByText('Unsorted')
    expect(unsortedHeadings.length).toBeGreaterThan(0)
  })

  it('does not render Lesson N subtitle (order is per-module)', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.queryByText('Lesson 1')).toBeNull()
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

  it('shows lesson action menu trigger when enrolled', async () => {
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: /Lesson actions: First Lesson/i })).toBeTruthy()
  })

  it('does not show lesson action menu trigger when not enrolled', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: false,
    })
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /Lesson actions:/i })).toBeNull()
  })

  it('marks lesson complete via menu action', async () => {
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Lesson actions: First Lesson/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Mark as complete/i }))
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', {
        lastPositionSec: 0,
        durationSec: 100,
        markComplete: true,
      })
    })
  })

  it('marks lesson incomplete via menu action when already completed', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })
    api.updateLessonProgress.mockResolvedValue({
      ok: true,
      lessonProgress: { lessonId: 'l1', completed: false, lastPositionSec: 0 },
    })

    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /Lesson actions: First Lesson/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Mark as incomplete/i }))
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', {
        lastPositionSec: 0,
        durationSec: 100,
        markIncomplete: true,
      })
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

  it('renders pricing section with selectable plans', async () => {
    renderCourseDetail()

    const pricing = await waitFor(() => screen.getByTestId('course-pricing'))
    expect(pricing).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Choose Your Plan' })).toBeTruthy()

    const popularBadge = screen.getByText('Most Popular')
    expect(popularBadge).toBeTruthy()

    const threeMonth = screen.getByTestId('pricing-plan-3month')
    expect(threeMonth.getAttribute('aria-checked')).toBe('true')

    const oneMonth = screen.getByTestId('pricing-plan-1month')
    fireEvent.click(oneMonth)
    expect(oneMonth.getAttribute('aria-checked')).toBe('true')
  })

  it('renders the hero and key page regions', async () => {
    renderCourseDetail()

    const heroHeading = await waitFor(() => screen.getByRole('heading', { level: 1, name: 'Test Course' }))
    expect(heroHeading).toBeTruthy()

    const curriculum = screen.getByRole('region', { name: /curriculum/i })
    expect(curriculum).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Curriculum' })).toBeTruthy()

    const pricingRegion = screen.getByRole('region', { name: /pricing/i })
    expect(pricingRegion).toBeTruthy()
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

  it('shows course not found when getCourse returns null', async () => {
    api.getCourse.mockResolvedValue(null as never)

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/Course not found/i)).toBeTruthy()
    })
    expect(screen.queryByText('First Lesson')).toBeNull()
  })

  it('shows error banner and does not render lessons when listCourseModules fails', async () => {
    api.listCourseModules.mockRejectedValue(new Error('Modules failed'))
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/Modules failed/i)).toBeTruthy()
    })
    expect(screen.queryByText('First Lesson')).toBeNull()
    expect(screen.queryByText('Second Lesson')).toBeNull()
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

  describe('module quiz badge', () => {
    it('shows passive Module quiz badge when enrolled and moduleQuiz.available', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.getByText('Module quiz')).toBeTruthy()
    })

    it('shows Start quiz link when enrolled and moduleQuiz.available', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /start quiz/i })).toBeTruthy()
      })
      const startLink = screen.getByRole('link', { name: /start quiz/i })
      expect(startLink.getAttribute('href')).toBe('/courses/c1/modules/m1/quiz')
    })

    it('navigates to module quiz route when Start quiz is clicked', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      const QuizStub = () => <div data-testid="quiz-page">Quiz shell</div>
      const router = createMemoryRouter(
        [
          { path: '/courses/:courseId', element: <CourseDetailPage /> },
          { path: '/courses/:courseId/modules/:moduleId/quiz', element: <QuizStub /> },
        ],
        { initialEntries: ['/courses/c1'] },
      )
      render(<RouterProvider router={router} />)

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /start quiz/i })).toBeTruthy()
      })
      fireEvent.click(screen.getByRole('link', { name: /start quiz/i }))

      await waitFor(() => {
        expect(screen.getByTestId('quiz-page')).toBeTruthy()
      })
    })

    it('does not show Module quiz badge when moduleQuiz is absent', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0 },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })

    it('does not show Module quiz badge when not enrolled', async () => {
      api.getCourse.mockResolvedValue({
        id: 'c1',
        title: 'Test Course',
        description: 'Test Description',
        status: 'PUBLISHED',
        enrolled: false,
      })
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })

    it('does not show Module quiz badge when moduleQuiz.available is false', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: false, servedCountN: 0 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })
  })

  it('clears hero and lesson list when route changes and the new course fails to load', async () => {
    api.getCourse.mockImplementation((courseId: string) => {
      if (courseId === 'c1') {
        return Promise.resolve({
          id: 'c1',
          title: 'Stale Hero Title',
          description: 'Test Description',
          status: 'PUBLISHED',
          enrolled: true,
        })
      }
      return Promise.reject(new ApiError('boom', 500))
    })

    const router = createMemoryRouter(
      [{ path: '/courses/:courseId', element: <CourseDetailPage /> }],
      { initialEntries: ['/courses/c1'] },
    )
    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Stale Hero Title' })).toBeTruthy()
    })
    expect(screen.getByText('First Lesson')).toBeTruthy()

    await router.navigate('/courses/c2')

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeTruthy()
    })
    await waitFor(() => {
      expect(screen.queryByText('Stale Hero Title')).toBeNull()
    })
    expect(screen.queryByText('First Lesson')).toBeNull()
  })
})
