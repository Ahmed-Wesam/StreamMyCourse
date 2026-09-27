import type { Course } from '../../lib/api/types'
import { courseNotFoundMessage } from '../../lib/apiUserMessages'

export function courseDetailHeroTitle(
  loading: boolean,
  course: Course | null,
  error: string | null,
): string {
  if (loading) return 'Loading…'
  if (course?.title) return course.title
  if (error === courseNotFoundMessage) return 'Course not found'
  if (error) return 'Unable to load course'
  return ''
}
