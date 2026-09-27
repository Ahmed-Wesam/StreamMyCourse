import type { Course, Lesson } from '../../lib/api/types'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'

type Props = {
  course: Course
  sortedLessons: Lesson[]
  moduleTitleById: Map<string, string>
  onAddLessonClick: () => void
  onDeleteLesson: (lessonId: string) => void
}

export function CourseManagementLessonsPanel({
  course,
  sortedLessons,
  moduleTitleById,
  onAddLessonClick,
  onDeleteLesson,
}: Props) {
  return (
    <Card className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-extrabold text-rs-navy">Lessons ({sortedLessons.length})</h2>
        {course.status === 'DRAFT' && (
          <Button type="button" size="sm" onClick={onAddLessonClick}>
            + Add Lesson
          </Button>
        )}
      </div>

      {sortedLessons.length === 0 ? (
        <div className="rounded-lg bg-rs-sky-2 py-12 text-center">
          <p className="text-rs-body">No lessons yet</p>
          {course.status === 'DRAFT' && (
            <p className="mt-1 text-sm text-rs-muted">Add your first lesson with a video</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {sortedLessons.map((lesson, index) => (
            <div
              key={lesson.id}
              className="flex items-center justify-between rounded-lg border border-rs-line p-4 transition-colors hover:bg-rs-sky-2/40"
            >
              <div className="flex items-center gap-4">
                <span className="font-semibold text-rs-muted">{index + 1}</span>
                <div>
                  <h3 className="font-semibold text-rs-navy">{lesson.title}</h3>
                  {moduleTitleById.get(lesson.moduleId) && (
                    <div className="mt-1 text-xs text-rs-muted">{moduleTitleById.get(lesson.moduleId)}</div>
                  )}
                  <div className="mt-1 flex items-center gap-2">
                    <Badge tone={lesson.videoStatus === 'ready' ? 'success' : 'blue'}>
                      {lesson.videoStatus === 'ready' ? '✓ Ready' : '⏳ Pending'}
                    </Badge>
                  </div>
                </div>
              </div>
              {course.status === 'DRAFT' && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Delete Lesson"
                  className="!text-red-700 hover:!bg-red-50"
                  onClick={() => void onDeleteLesson(lesson.id)}
                >
                  Delete
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
