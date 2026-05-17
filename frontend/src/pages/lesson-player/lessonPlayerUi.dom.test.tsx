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
  resolveNextModuleQuizHref,
  resolvePrevModuleQuizHref,
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

describe('resolveNextModuleQuizHref', () => {
  const modules: CourseModule[] = [
    { id: 'm1', title: 'Section 1', description: '', order: 0 },
    {
      id: 'm2',
      title: 'Quiz only',
      description: '',
      order: 1,
      moduleQuiz: { available: true, servedCountN: 2 },
    },
    { id: 'm3', title: 'Section 3', description: '', order: 2 },
  ]

  const lessonsWithLaterModule: Lesson[] = [
    {
      id: 'l1',
      title: 'Last in M1',
      order: 1,
      moduleId: 'm1',
      moduleOrder: 0,
      videoStatus: 'ready',
      duration: 120,
    },
    {
      id: 'l3',
      title: 'First in M3',
      order: 1,
      moduleId: 'm3',
      moduleOrder: 2,
      videoStatus: 'ready',
      duration: 120,
    },
  ]

  it('targets a following quiz-only module after the last lesson in the prior module', () => {
    const href = resolveNextModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l1',
      lessons: lessonsWithLaterModule,
      modules,
      playbackNavLocked: false,
    })
    expect(href).toMatchObject({ pathname: '/courses/c1/modules/m2/quiz' })
  })

  it('prefers the current module quiz before a later quiz-only module', () => {
    const modulesWithM1Quiz: CourseModule[] = [
      {
        id: 'm1',
        title: 'Section 1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
      modules[1]!,
      modules[2]!,
    ]
    const href = resolveNextModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l1',
      lessons: lessonsWithLaterModule,
      modules: modulesWithM1Quiz,
      playbackNavLocked: false,
    })
    expect(href).toMatchObject({ pathname: '/courses/c1/modules/m1/quiz' })
  })

  it('returns null when not on the last lesson in the module', () => {
    const href = resolveNextModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l1',
      lessons: [
        ...lessonsWithLaterModule,
        {
          id: 'l1b',
          title: 'Second in M1',
          order: 2,
          moduleId: 'm1',
          moduleOrder: 0,
          videoStatus: 'ready',
          duration: 60,
        },
      ],
      modules,
      playbackNavLocked: false,
    })
    expect(href).toBeNull()
  })
})

describe('resolvePrevModuleQuizHref', () => {
  const modules: CourseModule[] = [
    { id: 'm1', title: 'Section 1', description: '', order: 0 },
    {
      id: 'm2',
      title: 'Quiz only',
      description: '',
      order: 1,
      moduleQuiz: { available: true, servedCountN: 2 },
    },
    { id: 'm3', title: 'Section 3', description: '', order: 2 },
  ]

  it('targets a preceding quiz-only module from the first lesson in a later module', () => {
    const href = resolvePrevModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l3',
      lessons: [
        {
          id: 'l1',
          title: 'M1',
          order: 1,
          moduleId: 'm1',
          moduleOrder: 0,
          videoStatus: 'ready',
          duration: 120,
        },
        {
          id: 'l3',
          title: 'M3 first',
          order: 1,
          moduleId: 'm3',
          moduleOrder: 2,
          videoStatus: 'ready',
          duration: 120,
        },
      ],
      modules,
      playbackNavLocked: false,
    })
    expect(href).toMatchObject({ pathname: '/courses/c1/modules/m2/quiz' })
  })

  it('targets the prior module quiz when that module has lessons', () => {
    const href = resolvePrevModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l3',
      lessons: [
        {
          id: 'l1',
          title: 'M1',
          order: 1,
          moduleId: 'm1',
          moduleOrder: 0,
          videoStatus: 'ready',
          duration: 120,
        },
        {
          id: 'l3',
          title: 'M3 first',
          order: 1,
          moduleId: 'm3',
          moduleOrder: 2,
          videoStatus: 'ready',
          duration: 120,
        },
      ],
      modules: [
        {
          id: 'm1',
          title: 'Section 1',
          description: '',
          order: 0,
          moduleQuiz: { available: true, servedCountN: 2 },
        },
        modules[1]!,
        modules[2]!,
      ],
      playbackNavLocked: false,
    })
    expect(href).toMatchObject({ pathname: '/courses/c1/modules/m1/quiz' })
  })
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
          prevQuizHref={null}
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
