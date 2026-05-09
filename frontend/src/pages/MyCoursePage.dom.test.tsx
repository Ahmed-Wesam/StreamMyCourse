/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MyCoursePage from './MyCoursePage'

vi.mock('../lib/api', () => {
  return {
    listCourses: vi.fn(async () => [
      { id: 'c-1', title: 'Featured Course', description: 'Course description', status: 'PUBLISHED' },
    ]),
    listCourseModules: vi.fn(async () => [{ id: 'm-1', title: 'Module 1', description: '', order: 1 }]),
    listLessons: vi.fn(async () => [
      {
        id: 'l-1',
        title: 'Lesson 1',
        order: 1,
        moduleId: 'm-1',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 120,
      },
    ]),
    getCourseProgress: vi.fn(async () => ({
      courseId: 'c-1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l-1', completed: false, lastPositionSec: 45 }],
    })),
  }
})

describe('MyCoursePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders heading landmark and primary continue CTA', async () => {
    render(
      <MemoryRouter>
        <MyCoursePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /featured course/i })).toBeTruthy()
    })

    const cta = screen.getAllByRole('link', { name: /continue learning/i })[0]
    expect(cta.getAttribute('href')).toBe('/courses/c-1/lessons/l-1?t=45')
  })
})

