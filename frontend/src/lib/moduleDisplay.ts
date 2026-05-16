import type { CourseModule } from './api'

export function moduleDisplayTitle(modules: CourseModule[], moduleId: string): string {
  const title = modules.find((m) => m.id === moduleId)?.title?.trim()
  return title || 'Unknown module'
}
