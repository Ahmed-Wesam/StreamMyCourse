import type { CourseModule } from './api/types'

export function moduleDisplayTitle(modules: CourseModule[], moduleId: string): string {
  const title = modules.find((m) => m.id === moduleId)?.title?.trim()
  return title || 'Unknown module'
}
