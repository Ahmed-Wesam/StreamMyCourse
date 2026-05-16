import { describe, expect, it } from 'vitest'

import type { CourseModule, Lesson } from './api'
import {
  UNSORTED_SECTION_ID,
  groupLessonsByModule,
  type LessonModuleSection,
} from './lessonGrouping'

const lesson = (partial: Omit<Lesson, 'videoStatus'> & Partial<Pick<Lesson, 'videoStatus'>>): Lesson => ({
  videoStatus: 'ready',
  ...partial,
})

function sectionIds(sections: LessonModuleSection[]): string[] {
  return sections.map((s) => s.id)
}

describe('groupLessonsByModule', () => {
  it('returns empty sections when both lists are empty', () => {
    expect(groupLessonsByModule([], [])).toEqual([])
  })

  it('puts all lessons in Unsorted when modules is empty', () => {
    const lessons: Lesson[] = [
      lesson({ id: 'a', title: 'A', order: 1, moduleId: 'm1', moduleOrder: 0 }),
      lesson({ id: 'b', title: 'B', order: 2, moduleId: 'm2', moduleOrder: 1 }),
    ]
    const out = groupLessonsByModule(lessons, [])
    expect(out).toHaveLength(1)
    expect(out[0]).toMatchObject({
      id: UNSORTED_SECTION_ID,
      title: 'Unsorted',
    })
    expect(out[0].lessons.map((l) => l.id)).toEqual(['a', 'b'])
  })

  it('returns only Unsorted when every lesson references an unknown module', () => {
    const modules: CourseModule[] = [{ id: 'm1', title: 'Mod 1', description: '', order: 0 }]
    const lessons: Lesson[] = [
      lesson({ id: 'x', title: 'X', order: 1, moduleId: 'ghost', moduleOrder: 0 }),
      lesson({ id: 'y', title: 'Y', order: 2, moduleId: 'ghost', moduleOrder: 0 }),
    ]
    const out = groupLessonsByModule(lessons, modules)
    expect(sectionIds(out)).toEqual([UNSORTED_SECTION_ID])
    expect(out[0].lessons.map((l) => l.id)).toEqual(['x', 'y'])
  })

  it('orders known modules by module order, then appends Unsorted for orphans', () => {
    const modules: CourseModule[] = [
      { id: 'm2', title: 'Second', description: 'd2', order: 1 },
      { id: 'm1', title: 'First', description: '', order: 0 },
    ]
    const lessons: Lesson[] = [
      lesson({ id: 'o', title: 'Orphan', order: 1, moduleId: 'missing', moduleOrder: 99 }),
      lesson({ id: 'b', title: 'B', order: 1, moduleId: 'm2', moduleOrder: 1 }),
      lesson({ id: 'a', title: 'A', order: 1, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const out = groupLessonsByModule(lessons, modules)
    expect(sectionIds(out)).toEqual(['m1', 'm2', UNSORTED_SECTION_ID])
    expect(out[0]).toMatchObject({ id: 'm1', title: 'First', description: undefined })
    expect(out[0].lessons.map((l) => l.id)).toEqual(['a'])
    expect(out[1]).toMatchObject({ id: 'm2', title: 'Second', description: 'd2' })
    expect(out[1].lessons.map((l) => l.id)).toEqual(['b'])
    expect(out[2].lessons.map((l) => l.id)).toEqual(['o'])
  })

  it('sorts lessons within a module by (moduleOrder, order)', () => {
    const modules: CourseModule[] = [{ id: 'm1', title: 'M', description: '', order: 0 }]
    const lessons: Lesson[] = [
      lesson({ id: 'z', title: 'Z', order: 2, moduleId: 'm1', moduleOrder: 0 }),
      lesson({ id: 'w', title: 'W', order: 1, moduleId: 'm1', moduleOrder: 0 }),
    ]
    const out = groupLessonsByModule(lessons, modules)
    expect(out).toHaveLength(1)
    expect(out[0].lessons.map((l) => l.id)).toEqual(['w', 'z'])
  })

  it('keeps module sections that have no lessons but have an available quiz', () => {
    const modules: CourseModule[] = [
      { id: 'm1', title: 'Has', description: '', order: 0 },
      {
        id: 'm2',
        title: 'Quiz Only',
        description: '',
        order: 1,
        moduleQuiz: { available: true, servedCountN: 2 },
      },
    ]
    const lessons: Lesson[] = [lesson({ id: 'a', title: 'A', order: 1, moduleId: 'm1', moduleOrder: 0 })]
    const out = groupLessonsByModule(lessons, modules)
    expect(sectionIds(out)).toEqual(['m1', 'm2'])
    expect(out[1]).toMatchObject({ id: 'm2', title: 'Quiz Only', lessons: [] })
  })

  it('omits module sections that have neither lessons nor an available quiz', () => {
    const modules: CourseModule[] = [
      { id: 'm1', title: 'Has', description: '', order: 0 },
      { id: 'm2', title: 'Empty', description: '', order: 1 },
      {
        id: 'm3',
        title: 'Unavailable Quiz',
        description: '',
        order: 2,
        moduleQuiz: { available: false, servedCountN: 0 },
      },
    ]
    const lessons: Lesson[] = [lesson({ id: 'a', title: 'A', order: 1, moduleId: 'm1', moduleOrder: 0 })]
    const out = groupLessonsByModule(lessons, modules)
    expect(sectionIds(out)).toEqual(['m1'])
  })
})
