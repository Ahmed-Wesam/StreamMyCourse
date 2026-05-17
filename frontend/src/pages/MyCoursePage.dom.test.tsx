/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MyCoursePage from './MyCoursePage'

const courseOne = { id: 'c-1', title: 'Course One', description: 'First course', status: 'PUBLISHED' as const }
const courseTwo = { id: 'c-2', title: 'Course Two', description: 'Second course', status: 'PUBLISHED' as const }

vi.mock('../lib/api', () => {
  return {
    listCourses: vi.fn(async () => [courseOne, courseTwo]),
    listCourseModules: vi.fn(async () => [{ id: 'm-1', title: 'Module 1', description: '', order: 1 }]),
    listLessons: vi.fn(async (courseId: string) => [
      {
        id: `l-${courseId}`,
        title: `Lesson for ${courseId}`,
        order: 1,
        moduleId: 'm-1',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 120,
      },
    ]),
    getCourseProgress: vi.fn(async (courseId: string) => ({
      courseId,
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: `l-${courseId}`, completed: false, lastPositionSec: courseId === 'c-1' ? 45 : 0 }],
    })),
  }
})

describe('MyCoursePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders a Courses heading and a horizontal strip per course', async () => {
    render(
      <MemoryRouter>
        <MyCoursePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Courses' })).toBeTruthy()
    })

    expect(screen.getByRole('heading', { level: 2, name: 'Course One' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Course Two' })).toBeTruthy()

    const resumeCta = screen.getByRole('link', { name: 'Resume' })
    expect(resumeCta.getAttribute('href')).toBe('/courses/c-1/lessons/l-c-1?t=45')

    const continueCta = screen.getByRole('link', { name: 'Continue' })
    expect(continueCta.getAttribute('href')).toBe('/courses/c-2/lessons/l-c-2')
  })
})
