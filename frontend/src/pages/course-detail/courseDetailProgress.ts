import type { CourseProgress, Lesson, LessonProgressItem } from '../../lib/api/types'

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

export function getResumeLesson(
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): { lesson: Lesson; startTimeSec: number } | null {
  if (lessons.length === 0) return null

  const sortedLessons = [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)

  for (const lesson of sortedLessons) {
    const progress = courseProgress?.lessons.find((p) => p.lessonId === lesson.id)
    if (!progress || !progress.completed) {
      const startTimeSec = progress?.lastPositionSec ?? 0
      return { lesson, startTimeSec }
    }
  }

  return { lesson: sortedLessons[0], startTimeSec: 0 }
}
