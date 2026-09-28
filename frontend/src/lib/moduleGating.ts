import type { CourseModule, Lesson } from './api/types'

export function isModuleLocked(module: CourseModule | undefined): boolean {
  return module?.locked === true
}

function isLessonInLockedModule(lesson: Lesson, modules: CourseModule[]): boolean {
  const mod = modules.find((m) => m.id === lesson.moduleId)
  return isModuleLocked(mod)
}

export function isAccessibleLesson(lesson: Lesson, modules: CourseModule[]): boolean {
  return !isLessonInLockedModule(lesson, modules)
}

/** Module quiz the student may navigate to (available and not gated locked). */
export function hasNavigableModuleQuiz(
  module: CourseModule | undefined,
): module is CourseModule & { moduleQuiz: { available: true; servedCountN: number } } {
  if (module?.moduleQuiz?.available !== true) return false
  return !isModuleLocked(module)
}

export function resolveNextAccessibleLesson(
  sortedLessons: Lesson[],
  activeLessonIndex: number,
  modules: CourseModule[],
): Lesson | null {
  if (activeLessonIndex < 0) return null
  for (let i = activeLessonIndex + 1; i < sortedLessons.length; i++) {
    const lesson = sortedLessons[i]!
    if (isAccessibleLesson(lesson, modules)) return lesson
  }
  return null
}

export function resolvePrevAccessibleLesson(
  sortedLessons: Lesson[],
  activeLessonIndex: number,
  modules: CourseModule[],
): Lesson | null {
  if (activeLessonIndex < 0) return null
  for (let i = activeLessonIndex - 1; i >= 0; i--) {
    const lesson = sortedLessons[i]!
    if (isAccessibleLesson(lesson, modules)) return lesson
  }
  return null
}
