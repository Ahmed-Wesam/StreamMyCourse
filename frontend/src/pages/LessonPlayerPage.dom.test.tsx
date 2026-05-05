/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import LessonPlayerPage from './LessonPlayerPage'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listLessons: vi.fn(),
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
      { id: 'l1', title: 'Lesson 1', order: 1, videoStatus: 'ready' },
      { id: 'l2', title: 'Lesson 2', order: 2, videoStatus: 'ready', duration: 300 },
    ])
    api.getPlaybackUrl.mockResolvedValue({ url: 'https://example.com/lesson.mp4' })
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

  it('shows completion badge when lesson is completed', async () => {
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
      expect(screen.getByText('Completed')).toBeTruthy()
    })
  })

  it('shows "Done" badge on completed lessons in sidebar', async () => {
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
      const doneBadges = screen.getAllByText('Done')
      expect(doneBadges.length).toBeGreaterThan(0)
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

  it('shows "Mark as not done" button for completed lessons', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 120 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderLessonPlayer('/courses/c1/lessons/l1')

    const button = await screen.findByRole('button', { name: /Mark as not done/i })
    expect(button).toBeTruthy()
  })

  it('calls updateLessonProgress with markIncomplete when "Mark as not done" clicked', async () => {
    api.getCourseProgress
      .mockResolvedValueOnce({
        courseId: 'c1',
        totalReadyLessons: 2,
        completedCount: 1,
        percentComplete: 50,
        lessons: [
          { lessonId: 'l1', completed: true, lastPositionSec: 120 },
          { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        ],
      })
      .mockResolvedValueOnce({
        courseId: 'c1',
        totalReadyLessons: 2,
        completedCount: 0,
        percentComplete: 0,
        lessons: [
          { lessonId: 'l1', completed: false, lastPositionSec: 0 },
          { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        ],
      })

    renderLessonPlayer('/courses/c1/lessons/l1')

    const button = await screen.findByRole('button', { name: /Mark as not done/i })
    fireEvent.click(button)

    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', { lastPositionSec: 0, markIncomplete: true })
    })
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
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', { lastPositionSec: 10 })
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
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l2', { lastPositionSec: 300, markComplete: true })
    })
  })
})
