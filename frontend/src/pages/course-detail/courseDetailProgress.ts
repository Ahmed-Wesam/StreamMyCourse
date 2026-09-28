import type { Lesson, LessonProgressItem } from '../../lib/api/types'

/** 0–100 for the thumbnail bar, or null when no in-progress / completed state to show. */
export function lessonThumbnailProgressPercent(
  lesson: Lesson,
  progressItem: LessonProgressItem | undefined,
): number | null {
  if (!progressItem) return null
  if (progressItem.completed) return 100
  const pos = progressItem.lastPositionSec
  if (pos <= 0) return null
  const duration = lesson.duration
  if (duration != null && duration > 0) {
    return Math.min(100, Math.round((pos / duration) * 100))
  }
  return 12
}
