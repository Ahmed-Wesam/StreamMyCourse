/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import type { CourseModule, CourseProgress, Lesson } from '../../lib/api'
import {
  CourseLessonsSidebar,
  hasAvailableModuleQuiz,
  LessonPlaybackNavigation,
  LessonUpNextCard,
} from './lessonPlayerUi'

const lessons: Lesson[] = [
  {
    id: 'l1',
    title: 'Alpha',
    order: 1,
    moduleId: 'm1',
    moduleOrder: 0,
    videoStatus: 'ready',
    duration: 120,
  },
]

const modules: CourseModule[] = [
  { id: 'm1', title: 'Section 1', description: '', order: 0 },
]

const courseProgress: CourseProgress = {
  courseId: 'c1',
  totalReadyLessons: 1,
  completedCount: 0,
  percentComplete: 0,
  lessons: [{ lessonId: 'l1', completed: false, lastPositionSec: 0 }],
}

afterEach(() => {
  cleanup()
})

describe('hasAvailableModuleQuiz', () => {
  it('returns true only when moduleQuiz.available is true', () => {
    expect(hasAvailableModuleQuiz(undefined)).toBe(false)
    expect(hasAvailableModuleQuiz({ id: 'm1', title: 'M', description: '', order: 0 })).toBe(false)
    expect(
      hasAvailableModuleQuiz({
        id: 'm1',
        title: 'M',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 2 },
      }),
    ).toBe(true)
  })
})

describe('CourseLessonsSidebar', () => {
  it('does not mount curriculum controls when collapsed', () => {
    render(
      <MemoryRouter>
        <CourseLessonsSidebar
          error={null}
          lessons={lessons}
          modules={modules}
          courseId="c1"
          activeLessonId="l1"
          playbackNavLocked={false}
          courseProgress={courseProgress}
          sidebarOpen={false}
          onClose={() => undefined}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button', { name: 'Close curriculum' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Section 1' })).toBeNull()
  })

  it('renders curriculum when expanded', () => {
    render(
      <MemoryRouter>
        <CourseLessonsSidebar
          error={null}
          lessons={lessons}
          modules={modules}
          courseId="c1"
          activeLessonId="l1"
          playbackNavLocked={false}
          courseProgress={courseProgress}
          sidebarOpen={true}
          onClose={() => undefined}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: 'Close curriculum' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Section 1' })).toBeTruthy()
  })
})

describe('LessonPlaybackNavigation', () => {
  it('links Next to the module quiz when nextQuizHref is set', () => {
    render(
      <MemoryRouter>
        <LessonPlaybackNavigation
          courseId="c1"
          playbackNavLocked={false}
          prevLesson={null}
          nextLesson={lessons[0]!}
          nextQuizHref="/courses/c1/modules/m1/quiz"
        />
      </MemoryRouter>,
    )

    const next = screen.getByRole('link', { name: 'Next' })
    expect(next.getAttribute('href')).toBe('/courses/c1/modules/m1/quiz')
  })
})

describe('LessonUpNextCard', () => {
  it('renders the up-next title and description', () => {
    render(
      <LessonUpNextCard
        upNextTitle="Beta"
        upNextDescription="Continue to the next lesson"
        playbackNavLocked={false}
      />,
    )

    expect(screen.getByText('Beta')).toBeTruthy()
    expect(screen.getByText('Continue to the next lesson')).toBeTruthy()
  })
})
