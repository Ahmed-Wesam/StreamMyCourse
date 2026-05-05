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
  getCourseProgress: vi.fn(),
  updateLessonProgress: vi.fn(),
  enrollInCourse: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    getCourse: (...args: unknown[]) => api.getCourse(...args) as ReturnType<typeof mod.getCourse>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    getPlaybackUrl: (...args: unknown[]) =>
      api.getPlaybackUrl(...args) as ReturnType<typeof mod.getPlaybackUrl>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
    updateLessonProgress: (...args: unknown[]) =>
      api.updateLessonProgress(...args) as ReturnType<typeof mod.updateLessonProgress>,
    enrollInCourse: (...args: unknown[]) =>
      api.enrollInCourse(...args) as ReturnType<typeof mod.enrollInCourse>,
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
    api.getCourseProgress.mockReset()
    api.updateLessonProgress.mockReset()
    api.enrollInCourse.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Course',
      description: 'Desc',
      status: 'PUBLISHED',
    })
    api.listLessons.mockResolvedValue([
      { id: 'l1', title: 'Lesson 1', order: 1, videoStatus: 'ready' },
    ])
    api.getPlaybackUrl.mockResolvedValue({ url: 'https://example.com/lesson.mp4' })
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l1', completed: false, completedAt: null, lastPositionSec: 0 }],
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
})
