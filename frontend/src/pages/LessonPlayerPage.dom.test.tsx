/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import LessonPlayerPage from './LessonPlayerPage'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listLessons: vi.fn(),
  listCourseModules: vi.fn(),
  getPlaybackUrl: vi.fn(),
  enrollInCourse: vi.fn(),
  getCourseProgress: vi.fn(),
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
    getPlaybackUrl: (...args: unknown[]) =>
      api.getPlaybackUrl(...args) as ReturnType<typeof mod.getPlaybackUrl>,
    enrollInCourse: (...args: unknown[]) =>
      api.enrollInCourse(...args) as ReturnType<typeof mod.enrollInCourse>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
    updateLessonProgress: (...args: unknown[]) =>
      api.updateLessonProgress(...args) as ReturnType<typeof mod.updateLessonProgress>,
  }
})

function renderLessonPlayer(path = '/courses/c1/lessons/l1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/courses/:courseId/lessons/:lessonId" element={<LessonPlayerPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LessonPlayerPage', () => {
  beforeEach(() => {
    api.getCourse.mockReset()
    api.listLessons.mockReset()
    api.listCourseModules.mockReset()
    api.getPlaybackUrl.mockReset()
    api.enrollInCourse.mockReset()
    api.getCourseProgress.mockReset()
    api.updateLessonProgress.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Course',
      description: 'Desc',
      status: 'PUBLISHED',
    })
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'Alpha',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 400,
      },
      {
        id: 'l2',
        title: 'Beta',
        order: 2,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 300,
      },
      {
        id: 'l3',
        title: 'Gamma',
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
    api.getPlaybackUrl.mockResolvedValue({ url: 'https://example.com/lesson.mp4' })
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
    api.updateLessonProgress.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders the lesson video with playsInline for mobile Safari inline playback', async () => {
    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    expect(video.playsInline).toBe(true)
  })

  it('shows course not found when getCourse returns null', async () => {
    api.getCourse.mockResolvedValue(null as never)

    renderLessonPlayer()

    await waitFor(() => {
      expect(screen.getByText(/Course not found/i)).toBeTruthy()
    })
    expect(api.listLessons).not.toHaveBeenCalled()
    expect(api.getPlaybackUrl).not.toHaveBeenCalled()
  })

  it('shows Sign in to watch and locks sidebar when playback returns 401', async () => {
    api.getPlaybackUrl.mockRejectedValue(new ApiError('Authentication required', 401, 'unauthorized'))

    renderLessonPlayer()

    const signInHeading = await screen.findByRole('heading', { name: /Sign in to watch/i })
    expect(signInHeading.isConnected).toBe(true)
    expect(screen.getByRole('link', { name: /^Sign in$/i }).getAttribute('href')).toBe('/login')
    expect(screen.getAllByText('Locked').length).toBeGreaterThan(0)
  })

  it('shows Sign in to watch after enroll when playback still returns 401', async () => {
    api.getPlaybackUrl
      .mockRejectedValueOnce(new ApiError('Enrollment required', 403, 'enrollment_required'))
      .mockRejectedValueOnce(new ApiError('Authentication required', 401, 'unauthorized'))
    api.enrollInCourse.mockResolvedValue({ courseId: 'c1', enrolled: true })

    renderLessonPlayer()

    expect((await screen.findByRole('heading', { name: /Enroll to watch/i })).isConnected).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: /Enroll for free/i }))

    expect((await screen.findByRole('heading', { name: /Sign in to watch/i })).isConnected).toBe(true)
    expect(screen.queryByRole('heading', { name: /Enroll to watch/i })).toBeNull()
  })

  it('loads progress after playback URL succeeds', async () => {
    renderLessonPlayer()

    await waitFor(() => {
      expect(api.getCourseProgress).toHaveBeenCalledWith('c1')
    })
  })

  it('shows "Mark as Incomplete" when lesson is completed', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 120, completedAt: '2024-01-01T00:00:00Z' },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderLessonPlayer('/courses/c1/lessons/l1')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Mark as Incomplete/i })).toBeTruthy()
    })
  })

  it('shows completed checkmark on completed lessons in sidebar', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 120, completedAt: '2024-01-01T00:00:00Z' },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderLessonPlayer('/courses/c1/lessons/l2')

    await waitFor(() => {
      const checkmarks = screen.getAllByLabelText('Completed lesson')
      expect(checkmarks.length).toBeGreaterThan(0)
    })
  })

  it('renders progress bar with correct percentage', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 4,
      completedCount: 2,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 120 },
        { lessonId: 'l2', completed: true, lastPositionSec: 200 },
        { lessonId: 'l3', completed: false, lastPositionSec: 0 },
        { lessonId: 'l4', completed: false, lastPositionSec: 0 },
      ],
    })

    renderLessonPlayer()

    await waitFor(() => {
      expect(screen.getByText('50%')).toBeTruthy()
    })
  })

  it('renders a per-lesson progress bar that is capped below 100% until completed', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'Alpha',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 400,
      },
      {
        id: 'l2',
        title: 'Beta',
        order: 2,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 400,
      },
    ])
    api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Section 1', description: '', order: 0 }])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 200 },
        { lessonId: 'l2', completed: true, lastPositionSec: 400 },
      ],
    })

    renderLessonPlayer('/courses/c1/lessons/l1')

    // Module is open because it contains the active lesson.
    const bars = await waitFor(() => screen.getAllByLabelText('Lesson progress'))
    expect(bars.length).toBeGreaterThan(0)

    // Ensure at least one is not full width (incomplete), and at least one is full width (complete).
    const widths = bars
      .map((el) => el.firstElementChild as HTMLElement | null)
      .filter(Boolean)
      .map((el) => el?.style.width ?? '')

    expect(widths.some((w) => w === '100%')).toBe(true)
    expect(widths.some((w) => w && w !== '100%')).toBe(true)
  })

  it('shows "Mark as Complete" button for an incomplete lesson', async () => {
    renderLessonPlayer('/courses/c1/lessons/l1')
    expect(await screen.findByRole('button', { name: /Mark as Complete/i })).toBeTruthy()
  })

  it('calls updateLessonProgress with markComplete when "Mark as Complete" is clicked', async () => {
    renderLessonPlayer('/courses/c1/lessons/l1')

    const btn = await screen.findByRole('button', { name: /Mark as Complete/i })
    await waitFor(() => {
      expect(document.querySelector('video')).toBeTruthy()
      expect((btn as HTMLButtonElement).disabled).toBe(false)
    })
    const progressFetchesBefore = api.getCourseProgress.mock.calls.length
    fireEvent.click(btn)

    await waitFor(() => {
      const calls = api.updateLessonProgress.mock.calls
      expect(calls.some((c) => c[2]?.markComplete === true)).toBe(true)
    })

    // UI should immediately reflect completion.
    expect(await screen.findByRole('button', { name: /Mark as Incomplete/i })).toBeTruthy()

    await waitFor(() => {
      expect(api.getCourseProgress.mock.calls.length).toBeGreaterThan(progressFetchesBefore)
    })
  })

  it('groups sidebar by module and shows module headings', async () => {
    renderLessonPlayer('/courses/c1/lessons/l1')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Section 1' })).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: 'Section 2' })).toBeTruthy()
  })

  it('shows Unsorted sidebar section when a lesson references an unknown module', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'In Module One',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 400,
      },
      {
        id: 'l2',
        title: 'In Module Two',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 300,
      },
      {
        id: 'l3',
        title: 'Orphan Lesson',
        order: 1,
        moduleId: 'm-unknown',
        moduleOrder: 2,
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
      totalReadyLessons: 3,
      completedCount: 0,
      percentComplete: 0,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 0 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        { lessonId: 'l3', completed: false, lastPositionSec: 0 },
      ],
    })

    renderLessonPlayer('/courses/c1/lessons/l1')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Section 1' })).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: 'Section 2' })).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Unsorted/i })).toBeTruthy()
    })
    // openSections defaults via useEffect; avoid clicking an already-expanded toggle (collapses).
    await waitFor(() => {
      expect(screen.getByText(/Orphan Lesson/i)).toBeTruthy()
    })
    const unsortedToggle = screen.getByRole('button', { name: /Unsorted/i })
    if (
      unsortedToggle.getAttribute('aria-expanded') !== 'true' &&
      !screen.queryByText(/Orphan Lesson/i)
    ) {
      fireEvent.click(unsortedToggle)
    }
    await waitFor(() => {
      expect(screen.getByText(/Orphan Lesson/i)).toBeTruthy()
    })
  })

  it('navigates Next/Previous across modules in (moduleOrder, order) order', async () => {
    renderLessonPlayer('/courses/c1/lessons/l2')

    const nextLinks = await waitFor(() => screen.getAllByRole('link', { name: /Next/i }))
    expect(nextLinks.some((a) => a.getAttribute('href') === '/courses/c1/lessons/l3')).toBe(true)

    cleanup()
    renderLessonPlayer('/courses/c1/lessons/l3')
    const prevLinks = await waitFor(() => screen.getAllByRole('link', { name: /Prev|Previous/i }))
    expect(prevLinks.some((a) => a.getAttribute('href') === '/courses/c1/lessons/l2')).toBe(true)
  })

  it('shows an available module quiz as a lesson-like sidebar row', async () => {
    api.listCourseModules.mockResolvedValue([
      {
        id: 'm1',
        title: 'Section 1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])

    renderLessonPlayer('/courses/c1/lessons/l1')

    const quizLink = await screen.findByRole('link', { name: /Module quiz/i })
    expect(quizLink.getAttribute('href')).toBe('/courses/c1/modules/m1/quiz')
  })

  it('shows a quiz-only module in the sidebar', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'Only Lesson',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 400,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Lesson Section', description: '', order: 0 },
      {
        id: 'm2',
        title: 'Quiz Only Section',
        description: '',
        order: 1,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l1', completed: false, lastPositionSec: 0 }],
    })

    renderLessonPlayer('/courses/c1/lessons/l1')

    const quizOnlyToggle = await screen.findByRole('button', { name: 'Quiz Only Section' })
    if (quizOnlyToggle?.getAttribute('aria-expanded') !== 'true') {
      fireEvent.click(quizOnlyToggle)
    }
    const quizLink = await screen.findByRole('link', { name: /Module quiz/i })
    expect(quizLink.getAttribute('href')).toBe('/courses/c1/modules/m2/quiz')
  })

  it('sends Next to the module quiz before the next module lesson', async () => {
    api.listCourseModules.mockResolvedValue([
      {
        id: 'm1',
        title: 'Section 1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])

    renderLessonPlayer('/courses/c1/lessons/l2')

    const nextLinks = await waitFor(() => screen.getAllByRole('link', { name: /Next/i }))
    expect(nextLinks.some((a) => a.getAttribute('href') === '/courses/c1/modules/m1/quiz')).toBe(true)
    expect(nextLinks.some((a) => a.getAttribute('href') === '/courses/c1/lessons/l3')).toBe(false)
  })

  it('does not send Next to a quiz when moduleQuiz is absent', async () => {
    renderLessonPlayer('/courses/c1/lessons/l2')

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Module quiz/i })).toBeNull()
    })
    const nextLinks = screen.getAllByRole('link', { name: /Next/i })
    expect(nextLinks.some((a) => a.getAttribute('href') === '/courses/c1/modules/m1/quiz')).toBe(false)
    expect(nextLinks.some((a) => a.getAttribute('href') === '/courses/c1/lessons/l3')).toBe(true)
  })

  it('hides module quiz navigation when enrollment is required', async () => {
    api.listCourseModules.mockResolvedValue([
      {
        id: 'm1',
        title: 'Section 1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])
    api.getPlaybackUrl.mockRejectedValue(new ApiError('Enrollment required', 403, 'enrollment_required'))

    renderLessonPlayer('/courses/c1/lessons/l2')

    expect((await screen.findByRole('heading', { name: /Enroll to watch/i })).isConnected).toBe(true)
    expect(screen.queryByRole('link', { name: /Module quiz/i })).toBeNull()
    expect(
      screen
        .queryAllByRole('link')
        .some((a) => a.getAttribute('href') === '/courses/c1/modules/m1/quiz'),
    ).toBe(false)
  })

  it('does not render Lesson N subtitle in sidebar items', async () => {
    renderLessonPlayer('/courses/c1/lessons/l1')

    await waitFor(() => {
      expect(screen.getAllByText('Alpha').length).toBeGreaterThan(0)
    })
    expect(screen.queryByText('Lesson 1')).toBeNull()
  })

  it('shows error banner and does not render sidebar when listCourseModules fails', async () => {
    api.listCourseModules.mockRejectedValue(new Error('Modules failed'))
    renderLessonPlayer('/courses/c1/lessons/l1')

    await waitFor(() => {
      expect(screen.getByText(/Modules failed/i)).toBeTruthy()
    })
    expect(screen.queryByText('Alpha')).toBeNull()
  })

  it('counts failures when markComplete fails', async () => {
    api.updateLessonProgress.mockRejectedValue(new Error('Network error'))

    renderLessonPlayer('/courses/c1/lessons/l1')

    const button = await screen.findByRole('button', { name: /Mark as Complete/i })
    await waitFor(() => {
      expect(document.querySelector('video')).toBeTruthy()
      expect((button as HTMLButtonElement).disabled).toBe(false)
    })

    // Click 10 times to trigger circuit breaker, awaiting each click
    for (let i = 0; i < 10; i++) {
      fireEvent.click(button)
      await waitFor(() => {
        expect(api.updateLessonProgress).toHaveBeenCalledTimes(i + 1)
      })
    }

    // Wait briefly for state to settle
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 11th click should not call API (circuit breaker open)
    fireEvent.click(button)
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(api.updateLessonProgress).toHaveBeenCalledTimes(10)
  })

  it('calls progress update on video time update', async () => {
    // Mock Date.now to return increasing values to bypass throttling
    const now = Date.now()
    let timeOffset = 0
    vi.spyOn(Date, 'now').mockImplementation(() => now + timeOffset)

    renderLessonPlayer()

    // Wait for video to be present
    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // First time update should trigger progress update
    timeOffset = 0
    Object.defineProperty(video, 'currentTime', { writable: true, value: 10 })
    fireEvent.timeUpdate(video)

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', {
        lastPositionSec: 10,
        durationSec: 400,
      })
    })

    vi.restoreAllMocks()
  })

  it('calls progress update with markComplete on video ended', async () => {
    renderLessonPlayer('/courses/c1/lessons/l2')

    // Wait for video to be present
    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    fireEvent.ended(video)

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l2', {
        lastPositionSec: 300,
        durationSec: 300,
        markComplete: true,
      })
    })
  })

  it('stops progress updates after 10 consecutive failures (circuit breaker)', async () => {
    // Mock updateLessonProgress to always fail
    api.updateLessonProgress.mockRejectedValue(new Error('Network error'))

    // Mock Date.now to control timing
    const now = Date.now()
    let timeOffset = 0
    vi.spyOn(Date, 'now').mockImplementation(() => now + timeOffset)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // Trigger 10 failed updates (each with 15s between attempts)
    for (let i = 0; i < 10; i++) {
      timeOffset = i * 15000 // 15 seconds between each
      Object.defineProperty(video, 'currentTime', { writable: true, value: 10 + i * 10 })
      fireEvent.timeUpdate(video)
      await waitFor(() => {
        expect(api.updateLessonProgress).toHaveBeenCalledTimes(i + 1)
      })
    }

    // Circuit breaker should now be open - 11th attempt should not call API
    timeOffset = 160000 // More than 15s after last
    Object.defineProperty(video, 'currentTime', { writable: true, value: 200 })
    fireEvent.timeUpdate(video)

    // Wait a bit and verify no 11th call
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(api.updateLessonProgress).toHaveBeenCalledTimes(10)

    vi.restoreAllMocks()
  })

  it('throttles progress updates to 15 seconds minimum between attempts', async () => {
    const now = Date.now()
    let timeOffset = 0
    vi.spyOn(Date, 'now').mockImplementation(() => now + timeOffset)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // First update at t=0
    timeOffset = 0
    Object.defineProperty(video, 'currentTime', { writable: true, value: 10 })
    fireEvent.timeUpdate(video)
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(1)
    })

    // Second update at t=5s - should be throttled
    timeOffset = 5000
    Object.defineProperty(video, 'currentTime', { writable: true, value: 20 })
    fireEvent.timeUpdate(video)
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(api.updateLessonProgress).toHaveBeenCalledTimes(1)

    // Third update at t=20s - should go through (15s passed)
    timeOffset = 20000
    Object.defineProperty(video, 'currentTime', { writable: true, value: 30 })
    fireEvent.timeUpdate(video)
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(2)
    })

    vi.restoreAllMocks()
  })

  it('saves progress immediately on video pause (checkpoint)', async () => {
    const now = Date.now()
    vi.spyOn(Date, 'now').mockImplementation(() => now)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // First update to establish a baseline
    Object.defineProperty(video, 'currentTime', { writable: true, value: 10 })
    fireEvent.timeUpdate(video)
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(1)
    })

    // Pause should trigger immediate save (ignoring 15s throttle)
    Object.defineProperty(video, 'currentTime', { writable: true, value: 50 })
    fireEvent.pause(video)

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(2)
      expect(api.updateLessonProgress).toHaveBeenLastCalledWith('c1', 'l1', {
        lastPositionSec: 50,
        durationSec: 400,
      })
    })

    vi.restoreAllMocks()
  })

  it('stops saving after 20 identical timestamps in a row (same-position circuit breaker)', async () => {
    const now = Date.now()
    vi.spyOn(Date, 'now').mockImplementation(() => now)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // Repeatedly pause at same timestamp
    Object.defineProperty(video, 'currentTime', { writable: true, value: 999 })

    // Fire 25 pauses at same position
    for (let i = 0; i < 25; i++) {
      fireEvent.pause(video)
      await new Promise((resolve) => setTimeout(resolve, 10))
    }

    // Wait for any async operations
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Should have exactly 20 calls (first call sets position, next 19 increment streak to 19,
    // 21st call makes streak=20 and trips breaker, calls 21-25 blocked)
    const callCount = api.updateLessonProgress.mock.calls.length
    expect(callCount).toBe(20)

    // If position changes, circuit should reset and allow one more save
    Object.defineProperty(video, 'currentTime', { writable: true, value: 1000 })
    fireEvent.pause(video)
    await new Promise((resolve) => setTimeout(resolve, 50))
    const finalCount = api.updateLessonProgress.mock.calls.length
    expect(finalCount).toBe(callCount + 1)

    vi.restoreAllMocks()
  })

  it('saves progress when tab becomes hidden (visibilitychange checkpoint)', async () => {
    const now = Date.now()
    vi.spyOn(Date, 'now').mockImplementation(() => now)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // First update to establish a baseline
    Object.defineProperty(video, 'currentTime', { writable: true, value: 10 })
    fireEvent.timeUpdate(video)
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(1)
    })

    // Simulate visibilitychange to hidden
    Object.defineProperty(video, 'currentTime', { writable: true, value: 60 })
    Object.defineProperty(document, 'hidden', { writable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(2)
      expect(api.updateLessonProgress).toHaveBeenLastCalledWith('c1', 'l1', {
        lastPositionSec: 60,
        durationSec: 400,
      })
    })

    vi.restoreAllMocks()
  })

  it('saves progress on pagehide checkpoint', async () => {
    const now = Date.now()
    vi.spyOn(Date, 'now').mockImplementation(() => now)

    renderLessonPlayer()

    const video = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })

    // First update to establish a baseline
    Object.defineProperty(video, 'currentTime', { writable: true, value: 10 })
    fireEvent.timeUpdate(video)
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(1)
    })

    // Set video time and trigger pagehide
    Object.defineProperty(video, 'currentTime', { writable: true, value: 75 })
    fireEvent(window, new Event('pagehide'))

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledTimes(2)
      expect(api.updateLessonProgress).toHaveBeenLastCalledWith('c1', 'l1', {
        lastPositionSec: 75,
        durationSec: 400,
      })
    })

    vi.restoreAllMocks()
  })

  it('clears breadcrumb, lesson title, and video src when route changes and the new course fails to load', async () => {
    api.getCourse.mockImplementation((courseId: string) => {
      if (courseId === 'c1') {
        return Promise.resolve({
          id: 'c1',
          title: 'Stale Breadcrumb Course',
          description: 'Desc',
          status: 'PUBLISHED',
        })
      }
      return Promise.reject(new ApiError('boom', 500))
    })

    const router = createMemoryRouter(
      [{ path: '/courses/:courseId/lessons/:lessonId', element: <LessonPlayerPage /> }],
      { initialEntries: ['/courses/c1/lessons/l1'] },
    )
    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Alpha' })).toBeTruthy()
    })
    expect(screen.getByRole('link', { name: 'Stale Breadcrumb Course' })).toBeTruthy()

    const videoBeforeNav = await waitFor(() => {
      const el = document.querySelector('video')
      expect(el).not.toBeNull()
      return el as HTMLVideoElement
    })
    expect(videoBeforeNav.getAttribute('src')).toBeTruthy()

    await router.navigate('/courses/c2/lessons/l3')

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeTruthy()
    })
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: 'Stale Breadcrumb Course' })).toBeNull()
    })
    await waitFor(() => {
      expect(screen.queryByRole('heading', { level: 1, name: 'Alpha' })).toBeNull()
    })

    const videoAfter = document.querySelector('video')
    const srcAfter = videoAfter?.getAttribute('src')
    expect(srcAfter === null || srcAfter === '').toBe(true)
  })
})
