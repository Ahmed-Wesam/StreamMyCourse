import type { Course, Lesson } from '../../lib/api'

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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Lessons ({sortedLessons.length})</h2>
        {course.status === 'DRAFT' && (
          <button
            type="button"
            onClick={onAddLessonClick}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            + Add Lesson
          </button>
        )}
      </div>

      {sortedLessons.length === 0 ? (
        <div className="rounded-lg bg-gray-50 py-12 text-center">
          <p className="text-gray-600">No lessons yet</p>
          {course.status === 'DRAFT' && (
            <p className="text-sm text-gray-500 mt-1">Add your first lesson with a video</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {sortedLessons.map((lesson, index) => (
            <div
              key={lesson.id}
              className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <span className="text-gray-400 font-medium">{index + 1}</span>
                <div>
                  <h3 className="font-medium text-gray-900">{lesson.title}</h3>
                  {moduleTitleById.get(lesson.moduleId) && (
                    <div className="mt-1 text-xs text-gray-500">{moduleTitleById.get(lesson.moduleId)}</div>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        lesson.videoStatus === 'ready'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {lesson.videoStatus === 'ready' ? '✓ Ready' : '⏳ Pending'}
                    </span>
                  </div>
                </div>
              </div>
              {course.status === 'DRAFT' && (
                <button
                  type="button"
                  onClick={() => void onDeleteLesson(lesson.id)}
                  aria-label="Delete Lesson"
                  className="text-red-600 hover:text-red-800 text-sm px-3 py-1 hover:bg-red-50 rounded transition-colors"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
