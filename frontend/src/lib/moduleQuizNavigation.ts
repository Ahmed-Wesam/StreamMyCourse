import type { CourseProgress, Lesson } from './api'

export type ModuleQuizReturnTo = string | { pathname: string; search?: string }

export function courseDetailPath(courseId: string): string {
  return `/courses/${courseId}`
}

export function lessonPlayerPath(
  courseId: string,
  lessonId: string,
  startTimeSec?: number,
): ModuleQuizReturnTo {
  const pathname = `/courses/${courseId}/lessons/${lessonId}`
  if (startTimeSec != null && startTimeSec > 0) {
    return { pathname, search: `?t=${startTimeSec}` }
  }
  return pathname
}

function getResumeLesson(
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): { lesson: Lesson; startTimeSec: number } | null {
  if (lessons.length === 0) return null

  const sortedLessons = [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)

  for (const lesson of sortedLessons) {
    const progress = courseProgress?.lessons.find((p) => p.lessonId === lesson.id)
    if (!progress || !progress.completed) {
      return { lesson, startTimeSec: progress?.lastPositionSec ?? 0 }
    }
  }

  return { lesson: sortedLessons[0]!, startTimeSec: 0 }
}

export function modulePlayerReturnPath(
  courseId: string,
  moduleId: string,
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): ModuleQuizReturnTo | null {
  const moduleLessons = lessons
    .filter((l) => l.moduleId === moduleId)
    .sort((a, b) => a.order - b.order)
  if (moduleLessons.length === 0) return null

  const returnLesson = moduleLessons[moduleLessons.length - 1]!
  const progress = courseProgress?.lessons.find((p) => p.lessonId === returnLesson.id)
  const startTimeSec = progress?.lastPositionSec ?? 0
  return lessonPlayerPath(courseId, returnLesson.id, startTimeSec > 0 ? startTimeSec : undefined)
}

function pathFromReturnTo(returnTo: ModuleQuizReturnTo): string {
  if (typeof returnTo === 'string') return returnTo
  return returnTo.search ? `${returnTo.pathname}${returnTo.search}` : returnTo.pathname
}

function isModuleQuizReturnTo(value: unknown): value is ModuleQuizReturnTo {
  if (typeof value === 'string') {
    return value.startsWith('/courses/') && value.includes('/lessons/')
  }
  if (value && typeof value === 'object' && 'pathname' in value) {
    const pathname = (value as { pathname?: unknown }).pathname
    return typeof pathname === 'string' && pathname.startsWith('/courses/') && pathname.includes('/lessons/')
  }
  return false
}

function isPlayerReturnForCourse(returnTo: ModuleQuizReturnTo, courseId: string): boolean {
  const path = pathFromReturnTo(returnTo)
  return path.startsWith(`/courses/${courseId}/lessons/`)
}

export function moduleQuizLinkTo(
  courseId: string,
  moduleId: string,
  returnTo: ModuleQuizReturnTo,
): { pathname: string; state: { returnTo: ModuleQuizReturnTo } } {
  return {
    pathname: `/courses/${courseId}/modules/${moduleId}/quiz`,
    state: { returnTo },
  }
}

/** Accessible label for the module quiz back link, matching {@link resolveModuleQuizBackTo} targets. */
export function moduleQuizBackLabel(returnTo: ModuleQuizReturnTo): string {
  const path = pathFromReturnTo(returnTo)
  if (path.includes('/lessons/')) return 'Back to lesson'
  return 'Back to course'
}

function lessonIdFromReturnTo(returnTo: ModuleQuizReturnTo, courseId: string): string | null {
  const path = pathFromReturnTo(returnTo)
  const prefix = `/courses/${courseId}/lessons/`
  if (!path.startsWith(prefix)) return null
  const segment = path.slice(prefix.length).split('?')[0]?.split('/')[0]
  return segment?.trim() ? segment : null
}

export function resolveModuleQuizBackTo(
  courseId: string,
  moduleId: string,
  returnToFromState: unknown,
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): ModuleQuizReturnTo {
  if (isModuleQuizReturnTo(returnToFromState) && isPlayerReturnForCourse(returnToFromState, courseId)) {
    const lessonId = lessonIdFromReturnTo(returnToFromState, courseId)
    if (lessonId && lessons.some((lesson) => lesson.id === lessonId)) {
      return returnToFromState
    }
  }

  const modulePath = modulePlayerReturnPath(courseId, moduleId, lessons, courseProgress)
  if (modulePath) return modulePath

  const resume = getResumeLesson(lessons, courseProgress)
  if (resume) {
    return lessonPlayerPath(
      courseId,
      resume.lesson.id,
      resume.startTimeSec > 0 ? resume.startTimeSec : undefined,
    )
  }

  return courseDetailPath(courseId)
}
