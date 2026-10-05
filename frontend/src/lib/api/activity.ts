/**
 * Authenticated learning activity:
 * GET /me/activity — streak days and recent lesson, quiz, assignment, and certificate events.
 */

import { httpGet } from './client'

export type LearningActivityItem = {
  kind: string
  at: string
  title: string
  courseId: string
  resourceId: string
}

type LearningActivity = {
  streakDays: number
  items: LearningActivityItem[]
}

function normalizeItem(row: unknown): LearningActivityItem | null {
  if (!row || typeof row !== 'object') return null
  const record = row as Record<string, unknown>
  const kind = typeof record.kind === 'string' ? record.kind.trim() : ''
  const at = typeof record.at === 'string' ? record.at.trim() : ''
  const title = typeof record.title === 'string' ? record.title.trim() : ''
  if (!kind || !at || !title) return null
  return {
    kind,
    at,
    title,
    courseId: typeof record.courseId === 'string' ? record.courseId : '',
    resourceId: typeof record.resourceId === 'string' ? record.resourceId : '',
  }
}

export async function getMyActivity(): Promise<LearningActivity> {
  const raw = await httpGet<Record<string, unknown>>('/me/activity')
  const streakRaw = raw.streakDays
  const streakDays =
    typeof streakRaw === 'number' && Number.isFinite(streakRaw) ? Math.max(0, Math.floor(streakRaw)) : 0
  const items = Array.isArray(raw.items)
    ? raw.items.map(normalizeItem).filter((item): item is LearningActivityItem => item !== null)
    : []
  return { streakDays, items }
}
