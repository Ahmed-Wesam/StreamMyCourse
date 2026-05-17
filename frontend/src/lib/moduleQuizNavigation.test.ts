import { describe, expect, it } from 'vitest'

import {
  modulePlayerReturnPath,
  moduleQuizBackLabel,
  moduleQuizLinkTo,
  resolveModuleQuizBackTo,
} from './moduleQuizNavigation'
import type { CourseProgress, Lesson } from './api'

const lessons: Lesson[] = [
  { id: 'l1', title: 'A', order: 0, moduleId: 'm1', moduleOrder: 0, videoStatus: 'ready' },
  { id: 'l2', title: 'B', order: 1, moduleId: 'm1', moduleOrder: 0, videoStatus: 'ready' },
  { id: 'l3', title: 'C', order: 0, moduleId: 'm2', moduleOrder: 1, videoStatus: 'ready' },
]

const progress: CourseProgress = {
  courseId: 'c1',
  totalReadyLessons: 3,
  completedCount: 0,
  percentComplete: 0,
  lessons: [{ lessonId: 'l2', completed: false, lastPositionSec: 42 }],
}

describe('moduleQuizNavigation', () => {
  it('modulePlayerReturnPath uses the last lesson in the module with saved position', () => {
    expect(modulePlayerReturnPath('c1', 'm1', lessons, progress)).toEqual({
      pathname: '/courses/c1/lessons/l2',
      search: '?t=42',
    })
  })

  it('resolveModuleQuizBackTo prefers location state when lesson exists', () => {
    expect(resolveModuleQuizBackTo('c1', 'm1', '/courses/c1/lessons/l2', lessons, progress)).toBe(
      '/courses/c1/lessons/l2',
    )
  })

  it('resolveModuleQuizBackTo ignores location state when lesson is missing', () => {
    expect(resolveModuleQuizBackTo('c1', 'm1', '/courses/c1/lessons/l9', lessons, progress)).toEqual({
      pathname: '/courses/c1/lessons/l2',
      search: '?t=42',
    })
  })

  it('moduleQuizBackLabel matches return target', () => {
    expect(moduleQuizBackLabel('/courses/c1/lessons/l2')).toBe('Back to lesson')
    expect(moduleQuizBackLabel({ pathname: '/courses/c1/lessons/l2', search: '?t=42' })).toBe(
      'Back to lesson',
    )
    expect(moduleQuizBackLabel('/courses/c1')).toBe('Back to course')
  })

  it('resolveModuleQuizBackTo falls back to course detail when no lessons', () => {
    expect(resolveModuleQuizBackTo('c1', 'm1', null, [], null)).toBe('/courses/c1')
  })

  it('moduleQuizLinkTo carries returnTo in router state', () => {
    expect(moduleQuizLinkTo('c1', 'm1', '/courses/c1/lessons/l1')).toEqual({
      pathname: '/courses/c1/modules/m1/quiz',
      state: { returnTo: '/courses/c1/lessons/l1' },
    })
  })
})
