/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CourseModule, CourseProgress, Lesson } from '../../lib/api/types'
import {
  CourseLessonsSidebar,
  hasAvailableModuleQuiz,
  LessonPlaybackNavigation,
  LessonUpNextCard,
  resolveNextModuleQuizHref,
  resolvePrevModuleQuizHref,
} from './lessonPlayerUi'
import { LessonPlayerTabs } from './LessonPlayerTabs'

const lessonFilesApi = vi.hoisted(() => ({
  listLessonFiles: vi.fn(),
  getLessonFileDownloadUrl: vi.fn(),
}))

const lessonNotesApi = vi.hoisted(() => ({
  listLessonNotes: vi.fn(),
  createLessonNote: vi.fn(),
  updateLessonNote: vi.fn(),
  deleteLessonNote: vi.fn(),
}))

const assignmentsApi = vi.hoisted(() => ({
  listCourseAssignments: vi.fn(),
}))

vi.mock('../../lib/api/lessonFiles', () => ({
  listLessonFiles: (...args: unknown[]) => lessonFilesApi.listLessonFiles(...args),
  getLessonFileDownloadUrl: (...args: unknown[]) => lessonFilesApi.getLessonFileDownloadUrl(...args),
}))

vi.mock('../../lib/api/lessonNotes', () => ({
  listLessonNotes: (...args: unknown[]) => lessonNotesApi.listLessonNotes(...args),
  createLessonNote: (...args: unknown[]) => lessonNotesApi.createLessonNote(...args),
  updateLessonNote: (...args: unknown[]) => lessonNotesApi.updateLessonNote(...args),
  deleteLessonNote: (...args: unknown[]) => lessonNotesApi.deleteLessonNote(...args),
}))

vi.mock('../../lib/api/assignments', () => ({
  listCourseAssignments: (...args: unknown[]) => assignmentsApi.listCourseAssignments(...args),
}))

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

  it('skips locked quiz-only modules when resolving next quiz href', () => {
    const lockedModules: CourseModule[] = [
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      {
        id: 'm2',
        title: 'Locked quiz only',
        description: '',
        order: 1,
        locked: true,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
      {
        id: 'm3',
        title: 'Open quiz only',
        description: '',
        order: 2,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
    ]
    const href = resolveNextModuleQuizHref({
      courseId: 'c1',
      lessonId: 'l1',
      lessons: [
        {
          id: 'l1',
          title: 'Last in M1',
          order: 1,
          moduleId: 'm1',
          moduleOrder: 0,
          videoStatus: 'ready',
          duration: 120,
        },
      ],
      modules: lockedModules,
      playbackNavLocked: false,
    })
    expect(href).toMatchObject({ pathname: '/courses/c1/modules/m3/quiz' })
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

describe('LessonPlayerTabs', () => {
  beforeEach(() => {
    lessonFilesApi.listLessonFiles.mockReset()
    lessonNotesApi.listLessonNotes.mockReset()
    assignmentsApi.listCourseAssignments.mockReset()
    lessonFilesApi.listLessonFiles.mockResolvedValue([])
    lessonNotesApi.listLessonNotes.mockResolvedValue([])
    assignmentsApi.listCourseAssignments.mockResolvedValue([])
  })

  it('lists five tabs and shows overview course description', () => {
    render(
      <MemoryRouter>
        <LessonPlayerTabs
          courseId="c1"
          lessonId="l1"
          moduleId="m1"
          courseDescription="Course overview copy"
          activeModuleLabel="Module A"
          activeLessonTitle="Lesson One"
        />
      </MemoryRouter>,
    )

    for (const label of ['Overview', 'Resources', 'Downloads', 'Notes', 'Assignments']) {
      expect(screen.getByRole('tab', { name: label })).toBeTruthy()
    }
    expect(screen.getByRole('tabpanel').textContent).toMatch(/Course overview copy/)
  })

  it('loads lesson files and notes when content is enabled', async () => {
    render(
      <MemoryRouter>
        <LessonPlayerTabs
          courseId="c1"
          lessonId="l1"
          moduleId="m1"
          courseDescription=""
          activeModuleLabel="Module A"
          activeLessonTitle="Lesson One"
          contentEnabled
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(lessonFilesApi.listLessonFiles).toHaveBeenCalledWith('c1', 'l1')
      expect(lessonNotesApi.listLessonNotes).toHaveBeenCalledWith('c1', 'l1')
    })
  })

  it('shows resource empty state and lists this module assignment with locked state', async () => {
    assignmentsApi.listCourseAssignments.mockResolvedValue([
      {
        id: 'a1',
        title: 'Module write-up',
        moduleId: 'm1',
        status: 'published',
        passPercent: 70,
        countsTowardCertificate: false,
        locked: true,
        instructions: { mode: 'plain', text: 'Do it' },
        rubric: { mode: 'plain', text: '' },
        criteria: [{ id: 'c1', label: 'Quality', maxPoints: 10 }],
        myLatest: null,
      },
    ])

    render(
      <MemoryRouter>
        <LessonPlayerTabs
          courseId="c1"
          lessonId="l1"
          moduleId="m1"
          courseDescription=""
          activeModuleLabel="Module A"
          activeLessonTitle="Lesson One"
          contentEnabled
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(lessonFilesApi.listLessonFiles).toHaveBeenCalled()
      expect(assignmentsApi.listCourseAssignments).toHaveBeenCalledWith('c1', { moduleId: 'm1' })
    })

    fireEvent.click(screen.getByRole('tab', { name: 'Resources' }))
    expect(screen.getByTestId('lesson-player-tab-panel').textContent).toMatch(/no resources/i)

    fireEvent.click(screen.getByRole('tab', { name: 'Assignments' }))
    expect(screen.queryByText(/not available yet/i)).toBeNull()
    const link = screen.getByRole('link', { name: /Module write-up/i })
    expect(link.getAttribute('href')).toBe('/courses/c1/assignments/a1')
    expect(screen.getByText(/locked/i)).toBeTruthy()
  })

  it('opens PDF resources in a new tab via presigned url', async () => {
    lessonFilesApi.listLessonFiles.mockResolvedValue([
      {
        fileId: 'f1',
        title: 'Slides',
        kind: 'resource',
        fileType: 'pdf',
        byteSize: 100,
        status: 'ready',
      },
    ])
    lessonFilesApi.getLessonFileDownloadUrl.mockResolvedValue({ url: 'https://cdn.example/slides.pdf' })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    render(
      <MemoryRouter>
        <LessonPlayerTabs
          courseId="c1"
          lessonId="l1"
          moduleId="m1"
          courseDescription=""
          activeModuleLabel="Module A"
          activeLessonTitle="Lesson One"
          contentEnabled
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Slides')).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('tab', { name: 'Resources' }))
    fireEvent.click(screen.getByRole('button', { name: /Slides/i }))

    await waitFor(() => {
      expect(lessonFilesApi.getLessonFileDownloadUrl).toHaveBeenCalledWith('c1', 'l1', 'f1')
      expect(openSpy).toHaveBeenCalledWith('https://cdn.example/slides.pdf', '_blank', 'noopener,noreferrer')
    })

    openSpy.mockRestore()
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
