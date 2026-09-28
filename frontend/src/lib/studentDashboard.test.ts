import { describe, expect, it } from 'vitest'

import type { Course, CourseModule, CourseProgress, Lesson, PurchaseRecord } from './api/types'
import {
  aggregateDashboardStats,
  buildContinueHref,
  buildDashboardCourseRow,
  buildDashboardCourseRows,
  ownedPublishedCoursesForDashboard,
  resolveContinueTarget,
  type CourseDashboardLoadResult,
} from './studentDashboard'

const publishedCourse = (id: string, title?: string): Course => ({
  id,
  title: title ?? `Course ${id}`,
  description: '',
  status: 'PUBLISHED',
})

const draftCourse = (id: string): Course => ({
  id,
  title: `Draft ${id}`,
  description: '',
  status: 'DRAFT',
})

const purchase = (partial: Partial<PurchaseRecord> & Pick<PurchaseRecord, 'id' | 'productType' | 'status'>): PurchaseRecord => ({
  amountMinor: 1000,
  currency: 'usd',
  createdAt: '2026-01-01T00:00:00Z',
  ...partial,
})

const lesson = (partial: Omit<Lesson, 'videoStatus'> & Partial<Pick<Lesson, 'videoStatus'>>): Lesson => ({
  videoStatus: 'ready',
  ...partial,
})

const progressFor = (courseId: string, items: Array<{ lessonId: string; completed?: boolean; lastPositionSec?: number }>): CourseProgress => {
  const lessons = items.map((item) => ({
    lessonId: item.lessonId,
    completed: item.completed ?? false,
    lastPositionSec: item.lastPositionSec ?? 0,
  }))
  const completedCount = lessons.filter((l) => l.completed).length
  return {
    courseId,
    totalReadyLessons: lessons.length,
    completedCount,
    percentComplete: lessons.length ? Math.round((completedCount / lessons.length) * 100) : 0,
    lessons,
  }
}

describe('ownedPublishedCoursesForDashboard', () => {
  const catalog = [
    publishedCourse('c1', 'Alpha'),
    publishedCourse('c2', 'Beta'),
    draftCourse('d1'),
  ]

  it('returns no rows when there are no purchases', () => {
    expect(ownedPublishedCoursesForDashboard([], catalog)).toEqual([])
  })

  it('drops non-paid purchase rows', () => {
    const purchases = [
      purchase({ id: 'p1', productType: 'course', status: 'refunded', courseId: 'c1' }),
      purchase({ id: 'p2', productType: 'course', status: 'pending', courseId: 'c2' }),
    ]
    expect(ownedPublishedCoursesForDashboard(purchases, catalog)).toEqual([])
  })

  it('drops paid course id missing from catalog', () => {
    const purchases = [purchase({ id: 'p1', productType: 'course', status: 'paid', courseId: 'missing' })]
    expect(ownedPublishedCoursesForDashboard(purchases, catalog)).toEqual([])
  })

  it('includes paid course in catalog order and skips drafts', () => {
    const purchases = [
      purchase({ id: 'p1', productType: 'course', status: 'paid', courseId: 'c2' }),
      purchase({ id: 'p2', productType: 'course', status: 'paid', courseId: 'c1' }),
    ]
    expect(ownedPublishedCoursesForDashboard(purchases, catalog).map((c) => c.id)).toEqual(['c1', 'c2'])
  })

  it('bundle purchase yields every published catalog course in catalog order', () => {
    const purchases = [purchase({ id: 'b1', productType: 'bundle', status: 'paid' })]
    expect(ownedPublishedCoursesForDashboard(purchases, catalog).map((c) => c.id)).toEqual(['c1', 'c2'])
  })
})

describe('aggregateDashboardStats', () => {
  const okLoad = (
    courseId: string,
    percentComplete: number,
    modules: CourseModule[] = [],
  ): CourseDashboardLoadResult => ({
    status: 'ok',
    courseId,
    percentComplete,
    modules,
    lessons: [],
    progress: progressFor(courseId, []),
  })

  it('returns zero stats when there are no owned courses', () => {
    expect(aggregateDashboardStats(0, [])).toEqual({
      availability: 'empty',
      activeCourses: 0,
      overallProgressPercent: 0,
      quizzesPassed: { passed: 0, visible: 0 },
    })
  })

  it('computes unweighted mean of percentComplete for successful loads only', () => {
    const results: CourseDashboardLoadResult[] = [
      okLoad('c1', 40),
      okLoad('c2', 80),
    ]
    const stats = aggregateDashboardStats(2, results)
    expect(stats).toMatchObject({
      availability: 'ready',
      activeCourses: 2,
      overallProgressPercent: 60,
    })
  })

  it('counts quizzes only on modules with visible quiz', () => {
    const modules: CourseModule[] = [
      {
        id: 'm1',
        title: 'M1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 5, passed: true },
      },
      {
        id: 'm2',
        title: 'M2',
        description: '',
        order: 1,
        moduleQuiz: { available: false, servedCountN: 5, passed: false },
      },
      {
        id: 'm3',
        title: 'M3',
        description: '',
        order: 2,
        moduleQuiz: { available: true, servedCountN: 5, passed: false },
      },
    ]
    const stats = aggregateDashboardStats(1, [okLoad('c1', 10, modules)])
    expect(stats).toMatchObject({
      availability: 'ready',
      quizzesPassed: { passed: 1, visible: 2 },
    })
  })

  it('excludes failed course loads from mean and quiz fraction', () => {
    const modules: CourseModule[] = [
      {
        id: 'm1',
        title: 'M1',
        description: '',
        order: 0,
        moduleQuiz: { available: true, servedCountN: 5, passed: true },
      },
    ]
    const results: CourseDashboardLoadResult[] = [
      okLoad('c1', 100, modules),
      { status: 'error', courseId: 'c2' },
    ]
    const stats = aggregateDashboardStats(2, results)
    expect(stats).toMatchObject({
      availability: 'ready',
      activeCourses: 1,
      overallProgressPercent: 100,
      quizzesPassed: { passed: 1, visible: 1 },
    })
  })

  it('marks stats unavailable when owned courses exist but every load failed', () => {
    const results: CourseDashboardLoadResult[] = [
      { status: 'error', courseId: 'c1' },
      { status: 'error', courseId: 'c2' },
    ]
    expect(aggregateDashboardStats(2, results)).toEqual({
      availability: 'unavailable',
      activeCourses: 0,
      overallProgressPercent: null,
      quizzesPassed: null,
    })
  })
})

describe('resolveContinueTarget', () => {
  const modules: CourseModule[] = [
    { id: 'm1', title: 'Mod 1', description: '', order: 0 },
    { id: 'm2', title: 'Mod 2', description: '', order: 1, locked: true },
    { id: 'm3', title: 'Mod 3', description: '', order: 2 },
  ]

  it('picks the first incomplete unlocked lesson in moduleOrder then order', () => {
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'L1', order: 0, moduleId: 'm1', moduleOrder: 0 }),
      lesson({ id: 'l2', title: 'L2', order: 1, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const progress = progressFor('c1', [
      { lessonId: 'l1', completed: true, lastPositionSec: 12 },
      { lessonId: 'l2', completed: false, lastPositionSec: 45 },
    ])
    expect(resolveContinueTarget(lessons, modules, progress)).toEqual({
      kind: 'lesson',
      lessonId: 'l2',
      startTimeSec: 45,
    })
  })

  it('skips incomplete lessons in locked modules', () => {
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'L1', order: 0, moduleId: 'm1', moduleOrder: 0 }),
      lesson({ id: 'l2', title: 'L2', order: 0, moduleId: 'm2', moduleOrder: 1 }),
      lesson({ id: 'l3', title: 'L3', order: 0, moduleId: 'm3', moduleOrder: 2 }),
    ]
    const progress = progressFor('c1', [
      { lessonId: 'l1', completed: true },
      { lessonId: 'l2', completed: false },
      { lessonId: 'l3', completed: false },
    ])
    expect(resolveContinueTarget(lessons, modules, progress)).toEqual({
      kind: 'lesson',
      lessonId: 'l3',
      startTimeSec: 0,
    })
  })

  it('falls back to earliest unlocked unpassed visible quiz when incomplete lessons are locked', () => {
    const lockedModules: CourseModule[] = [
      {
        id: 'm1',
        title: 'Mod 1',
        description: '',
        order: 0,
        locked: true,
        moduleQuiz: { available: true, servedCountN: 5, passed: false },
      },
      {
        id: 'm2',
        title: 'Mod 2',
        description: '',
        order: 1,
        moduleQuiz: { available: true, servedCountN: 5, passed: false },
      },
    ]
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'L1', order: 0, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const progress = progressFor('c1', [{ lessonId: 'l1', completed: false }])
    expect(resolveContinueTarget(lessons, lockedModules, progress)).toEqual({
      kind: 'quiz',
      moduleId: 'm2',
    })
  })

  it('returns blocked when no quiz fallback exists for locked incomplete lessons', () => {
    const lockedOnly: CourseModule[] = [
      { id: 'm1', title: 'Mod 1', description: '', order: 0, locked: true },
    ]
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'L1', order: 0, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const progress = progressFor('c1', [{ lessonId: 'l1', completed: false }])
    expect(resolveContinueTarget(lessons, lockedOnly, progress)).toEqual({ kind: 'blocked' })
  })

  it('replays the first lesson when every lesson is complete (legacy resume behavior)', () => {
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'L1', order: 0, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const progress = progressFor('c1', [{ lessonId: 'l1', completed: true }])
    expect(resolveContinueTarget(lessons, modules, progress)).toEqual({
      kind: 'lesson',
      lessonId: 'l1',
      startTimeSec: 0,
    })
  })
})

describe('buildContinueHref', () => {
  const courseId = 'course-1'

  it('builds lesson href with resume time when startTimeSec > 0', () => {
    expect(
      buildContinueHref(courseId, { kind: 'lesson', lessonId: 'l9', startTimeSec: 90 }),
    ).toBe('/courses/course-1/lessons/l9?t=90')
  })

  it('omits time query when startTimeSec is zero', () => {
    expect(
      buildContinueHref(courseId, { kind: 'lesson', lessonId: 'l9', startTimeSec: 0 }),
    ).toBe('/courses/course-1/lessons/l9')
  })

  it('builds quiz and blocked (course overview) hrefs', () => {
    expect(buildContinueHref(courseId, { kind: 'quiz', moduleId: 'm2' })).toBe(
      '/courses/course-1/modules/m2/quiz',
    )
    expect(buildContinueHref(courseId, { kind: 'blocked' })).toBe('/courses/course-1')
  })
})

describe('buildDashboardCourseRow', () => {
  const course = publishedCourse('c1', 'Alpha')

  it('builds subline with module index and lesson title for lesson continue target', () => {
    const modules: CourseModule[] = [
      { id: 'm1', title: 'Intro', description: '', order: 0 },
      { id: 'm2', title: 'Core', description: '', order: 1 },
    ]
    const lessons: Lesson[] = [
      lesson({ id: 'l1', title: 'Welcome', order: 0, moduleId: 'm1', moduleOrder: 0 }),
      lesson({ id: 'l2', title: 'Deep dive', order: 0, moduleId: 'm2', moduleOrder: 1 }),
    ]
    const load: CourseDashboardLoadResult = {
      status: 'ok',
      courseId: 'c1',
      percentComplete: 50,
      modules,
      lessons,
      progress: progressFor('c1', [
        { lessonId: 'l1', completed: true },
        { lessonId: 'l2', completed: false },
      ]),
    }
    const row = buildDashboardCourseRow(course, load)
    expect(row).toMatchObject({
      courseId: 'c1',
      title: 'Alpha',
      percentComplete: 50,
      subline: { moduleIndex: 2, moduleCount: 2, lessonTitle: 'Deep dive' },
      continueHref: '/courses/c1/lessons/l2',
    })
  })

  it('marks progress unavailable on failed load', () => {
    const row = buildDashboardCourseRow(course, { status: 'error', courseId: 'c1' })
    expect(row.percentComplete).toBe('unavailable')
    expect(row.continueHref).toBe('/courses/c1')
  })
})

describe('buildDashboardCourseRows', () => {
  it('returns no rows when there are no purchases', () => {
    expect(buildDashboardCourseRows([], [])).toEqual([])
  })
})
