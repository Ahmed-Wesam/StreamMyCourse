import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listInstructorCourses,
  listLessons,
  createCourse,
  publishCourse,
  deleteCourse,
  type Course,
} from '../lib/api'

export default function InstructorDashboard() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newCourseTitle, setNewCourseTitle] = useState('')
  const [newCourseDescription, setNewCourseDescription] = useState('')
  const [creating, setCreating] = useState(false)
  const [publishing, setPublishing] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lessonCounts, setLessonCounts] = useState<Record<string, number>>({})

  const loadCourses = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listInstructorCourses()
      setCourses(data)

      const counts: Record<string, number> = {}
      await Promise.all(
        data.map(async (course) => {
          try {
            const lessons = await listLessons(course.id)
            counts[course.id] = lessons.length
          } catch {
            counts[course.id] = 0
          }
        }),
      )
      setLessonCounts(counts)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load courses')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadCourses()
  }, [loadCourses])

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCourseTitle.trim()) return

    setCreating(true)
    setError(null)

    try {
      const result = await createCourse({
        title: newCourseTitle,
        description: newCourseDescription,
      })
      setShowCreateModal(false)
      setNewCourseTitle('')
      setNewCourseDescription('')
      // Navigate to course management page
      navigate(`/courses/${result.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create course')
    } finally {
      setCreating(false)
    }
  }

  const handlePublish = async (courseId: string) => {
    setPublishing(courseId)
    setError(null)

    try {
      await publishCourse(courseId)
      await loadCourses()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish course')
    } finally {
      setPublishing(null)
    }
  }

  const handleDelete = async (courseId: string) => {
    if (!confirm('Are you sure you want to delete this course?')) return

    setDeleting(courseId)
    setError(null)

    try {
      await deleteCourse(courseId)
      await loadCourses()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete course')
    } finally {
      setDeleting(null)
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="mb-8 h-8 w-1/4 rounded bg-gray-200" />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-56 rounded-lg bg-gray-200" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <>
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Instructor Dashboard</h1>
            <p className="text-gray-600 mt-1">Manage your courses and content</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            + Create New Course
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {courses.length === 0 ? (
          <div className="rounded-lg bg-white py-16 text-center shadow-sm">
            <h3 className="mb-2 text-xl font-semibold text-gray-900">No courses yet</h3>
            <p className="text-gray-600 mb-6">Create your first course to get started</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Create Your First Course
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {courses.map((course) => (
              <div
                key={course.id}
                className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="aspect-video overflow-hidden bg-slate-800">
                  {course.thumbnailUrl ? (
                    <img
                      src={course.thumbnailUrl}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-slate-500">
                      No thumbnail
                    </div>
                  )}
                </div>
                <div className="p-6">
                  <div className="mb-4 flex items-start justify-between">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        course.status === 'PUBLISHED'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {course.status}
                    </span>
                    <span className="text-sm text-gray-500">
                      {lessonCounts[course.id] ?? '—'} lessons
                    </span>
                  </div>

                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{course.title}</h3>
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">{course.description}</p>

                  <div className="flex gap-2">
                    <button
                      onClick={() => navigate(`/courses/${course.id}`)}
                      className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                    >
                      Manage
                    </button>

                    {course.status === 'DRAFT' && (
                      <button
                        onClick={() => handlePublish(course.id)}
                        disabled={publishing === course.id}
                        className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
                      >
                        {publishing === course.id ? 'Publishing...' : 'Publish'}
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(course.id)}
                      disabled={deleting === course.id}
                      className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium disabled:opacity-50"
                    >
                      {deleting === course.id ? '...' : 'Delete'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Course Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Create New Course</h2>
              <form onSubmit={handleCreateCourse}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Course Title *
                  </label>
                  <input
                    type="text"
                    value={newCourseTitle}
                    onChange={(e) => setNewCourseTitle(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., Introduction to Python"
                    required
                  />
                </div>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={newCourseDescription}
                    onChange={(e) => setNewCourseDescription(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                    placeholder="Brief description of your course..."
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating || !newCourseTitle.trim()}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {creating ? 'Creating...' : 'Create Course'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
    </>
  )
}
