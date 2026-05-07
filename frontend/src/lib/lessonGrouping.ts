import type { CourseModule, Lesson } from './api'

export type LessonModuleSection = {
  id: string
  title: string
  description?: string
  lessons: Lesson[]
}

/** Synthetic section id for lessons whose moduleId is missing from modules. */
export const UNSORTED_SECTION_ID = '__unsorted__'

function compareLessonOrdering(a: Lesson, b: Lesson): number {
  return a.moduleOrder - b.moduleOrder || a.order - b.order
}

/**
 * Builds ordered lesson sections: one per known module (with lessons),
 * stable module order via `CourseModule.order`, then optional Unsorted tail.
 */
export function groupLessonsByModule(lessons: Lesson[], modules: CourseModule[]): LessonModuleSection[] {
  const sortedLessons = [...lessons].sort(compareLessonOrdering)
  const moduleIdSet = new Set(modules.map((m) => m.id))
  const sortedModules = [...modules].sort((a, b) => a.order - b.order)

  const sections: LessonModuleSection[] = []

  for (const mod of sortedModules) {
    const moduleLessons = sortedLessons
      .filter((l) => l.moduleId === mod.id)
      .sort(compareLessonOrdering)
    if (moduleLessons.length === 0) continue
    sections.push({
      id: mod.id,
      title: mod.title,
      description: mod.description ? mod.description : undefined,
      lessons: moduleLessons,
    })
  }

  const orphanLessons = sortedLessons.filter((l) => !moduleIdSet.has(l.moduleId))
  if (orphanLessons.length > 0) {
    sections.push({
      id: UNSORTED_SECTION_ID,
      title: 'Unsorted',
      lessons: orphanLessons,
    })
  }

  return sections
}
