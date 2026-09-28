import type {
  Course,
  CourseModule,
  CourseProgress,
  Lesson,
  PurchaseRecord,
} from './api/types'
import { isAccessibleLesson } from './moduleGating'
import { ownedCoursesFromPurchases } from './ownedFromPurchases'

type ContinueTarget =
  | { kind: 'lesson'; lessonId: string; startTimeSec: number }
  | { kind: 'quiz'; moduleId: string }
  /** No accessible lesson or quiz (e.g. gated); dashboard may link to course overview. */
  | { kind: 'blocked' }

export type CourseDashboardLoadResult =
  | {
      status: 'ok'
      courseId: string
      percentComplete: number
      modules: CourseModule[]
      lessons: Lesson[]
      progress: CourseProgress
    }
  | { status: 'error'; courseId: string }

export type StudentDashboardStats =
  | {
      availability: 'empty'
      activeCourses: 0
      overallProgressPercent: 0
      quizzesPassed: { passed: 0; visible: 0 }
    }
  | {
      availability: 'ready'
      activeCourses: number
      overallProgressPercent: number
      quizzesPassed: { passed: number; visible: number }
    }
  | {
      availability: 'unavailable'
      activeCourses: 0
      overallProgressPercent: null
      quizzesPassed: null
    }

type DashboardCourseSubline = {
  moduleIndex: number
  moduleCount: number
  lessonTitle: string
}

export type StudentDashboardCourseRow = {
  courseId: string
  title: string
  percentComplete: number | 'unavailable'
  subline: DashboardCourseSubline | null
  continueHref: string
}

function compareLessonOrdering(a: Lesson, b: Lesson): number {
  return a.moduleOrder - b.moduleOrder || a.order - b.order
}

function sortedModules(modules: CourseModule[]): CourseModule[] {
  return [...modules].sort((a, b) => a.order - b.order)
}

function progressByLessonId(progress: CourseProgress): Map<string, CourseProgress['lessons'][number]> {
  return new Map(progress.lessons.map((item) => [item.lessonId, item]))
}

function tallyVisibleQuizzes(modules: CourseModule[]): { passed: number; visible: number } {
  let passed = 0
  let visible = 0
  for (const mod of modules) {
    if (mod.moduleQuiz?.available !== true) continue
    visible++
    if (mod.moduleQuiz.passed === true) passed++
  }
  return { passed, visible }
}

/** Paid purchases mapped to published catalog courses in catalog list order (RS-9). */
export function ownedPublishedCoursesForDashboard(
  purchases: PurchaseRecord[],
  catalog: Course[],
): Course[] {
  const scope = ownedCoursesFromPurchases(purchases)
  const publishedInOrder = catalog.filter((course) => course.status === 'PUBLISHED')
  if (scope.ownsAllPublished) return publishedInOrder
  return publishedInOrder.filter((course) => scope.courseIds.has(course.id))
}

export function aggregateDashboardStats(
  ownedCourseCount: number,
  loadResults: CourseDashboardLoadResult[],
): StudentDashboardStats {
  if (ownedCourseCount === 0) {
    return {
      availability: 'empty',
      activeCourses: 0,
      overallProgressPercent: 0,
      quizzesPassed: { passed: 0, visible: 0 },
    }
  }

  const successful = loadResults.filter((row): row is Extract<CourseDashboardLoadResult, { status: 'ok' }> => row.status === 'ok')
  if (successful.length === 0) {
    return {
      availability: 'unavailable',
      activeCourses: 0,
      overallProgressPercent: null,
      quizzesPassed: null,
    }
  }

  const overallProgressPercent =
    successful.reduce((sum, row) => sum + row.percentComplete, 0) / successful.length

  let passed = 0
  let visible = 0
  for (const row of successful) {
    const tally = tallyVisibleQuizzes(row.modules)
    passed += tally.passed
    visible += tally.visible
  }

  return {
    availability: 'ready',
    activeCourses: successful.length,
    overallProgressPercent,
    quizzesPassed: { passed, visible },
  }
}

/**
 * Next continue action for a course: first incomplete accessible lesson, else earliest
 * unlocked unpassed visible quiz, else course overview (RS-9).
 */
export function resolveContinueTarget(
  lessons: Lesson[],
  modules: CourseModule[],
  progress: CourseProgress,
): ContinueTarget {
  const byLesson = progressByLessonId(progress)
  const orderedLessons = [...lessons].sort(compareLessonOrdering)

  for (const lesson of orderedLessons) {
    const item = byLesson.get(lesson.id)
    if (item?.completed === true) continue
    if (!isAccessibleLesson(lesson, modules)) continue
    return {
      kind: 'lesson',
      lessonId: lesson.id,
      startTimeSec: item?.lastPositionSec ?? 0,
    }
  }

  const hasIncompleteLesson = orderedLessons.some((lesson) => {
    const item = byLesson.get(lesson.id)
    return item?.completed !== true
  })

  if (!hasIncompleteLesson) {
    const replay = orderedLessons[0]
    if (!replay) return { kind: 'blocked' }
    return { kind: 'lesson', lessonId: replay.id, startTimeSec: 0 }
  }

  for (const mod of sortedModules(modules)) {
    if (mod.locked === true) continue
    if (mod.moduleQuiz?.available !== true) continue
    if (mod.moduleQuiz.passed === true) continue
    return { kind: 'quiz', moduleId: mod.id }
  }

  return { kind: 'blocked' }
}

export function buildContinueHref(courseId: string, target: ContinueTarget): string {
  switch (target.kind) {
    case 'lesson': {
      const base = `/courses/${courseId}/lessons/${target.lessonId}`
      return target.startTimeSec > 0 ? `${base}?t=${target.startTimeSec}` : base
    }
    case 'quiz':
      return `/courses/${courseId}/modules/${target.moduleId}/quiz`
    case 'blocked':
      return `/courses/${courseId}`
  }
}

function dashboardSublineForTarget(
  target: ContinueTarget,
  lessons: Lesson[],
  modules: CourseModule[],
): DashboardCourseSubline | null {
  if (target.kind !== 'lesson') return null
  const lesson = lessons.find((row) => row.id === target.lessonId)
  if (!lesson) return null
  const orderedModules = sortedModules(modules)
  const moduleIndex = orderedModules.findIndex((mod) => mod.id === lesson.moduleId)
  if (moduleIndex < 0) return null
  return {
    moduleIndex: moduleIndex + 1,
    moduleCount: orderedModules.length,
    lessonTitle: lesson.title,
  }
}

export function buildDashboardCourseRow(
  course: Course,
  loadResult: CourseDashboardLoadResult,
): StudentDashboardCourseRow {
  if (loadResult.status === 'error') {
    return {
      courseId: course.id,
      title: course.title,
      percentComplete: 'unavailable',
      subline: null,
      continueHref: buildContinueHref(course.id, { kind: 'blocked' }),
    }
  }

  const target = resolveContinueTarget(loadResult.lessons, loadResult.modules, loadResult.progress)

  return {
    courseId: course.id,
    title: course.title,
    percentComplete: loadResult.percentComplete,
    subline: dashboardSublineForTarget(target, loadResult.lessons, loadResult.modules),
    continueHref: buildContinueHref(course.id, target),
  }
}

export function buildDashboardCourseRows(
  ownedCourses: Course[],
  loadResults: CourseDashboardLoadResult[],
): StudentDashboardCourseRow[] {
  if (ownedCourses.length === 0) return []
  const byCourseId = new Map(loadResults.map((row) => [row.courseId, row]))
  return ownedCourses.map((course) => {
    const loadResult = byCourseId.get(course.id) ?? { status: 'error' as const, courseId: course.id }
    return buildDashboardCourseRow(course, loadResult)
  })
}
