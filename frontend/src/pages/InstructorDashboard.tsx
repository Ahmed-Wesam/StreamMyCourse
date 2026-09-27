import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listInstructorCourses,
  listLessons,
  createCourse,
  publishCourse,
  deleteCourse,
} from '../lib/api/catalog'
import type { Course } from '../lib/api/types'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { usePageTitle } from '../lib/page-title'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'

export default function InstructorDashboard() {
  usePageTitle('Dashboard')
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
      setError(catalogApiUserMessage(err, 'loadCourses'))
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
      navigate(`/courses/${result.id}`)
    } catch (err) {
      setError(catalogApiUserMessage(err, 'createCourse'))
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
      setError(catalogApiUserMessage(err, 'publishCourse'))
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
      setError(catalogApiUserMessage(err, 'deleteCourse'))
    } finally {
      setDeleting(null)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
        <div className="animate-pulse">
          <div className="mb-8 h-8 w-1/4 rounded bg-rs-sky-2" />
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-56 rounded-lg bg-rs-sky-2" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-rs-navy">Instructor Dashboard</h1>
          <p className="mt-1 text-rs-body">Manage your courses and content</p>
        </div>
        <Button type="button" onClick={() => setShowCreateModal(true)}>
          + Create New Course
        </Button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {courses.length === 0 ? (
        <Card className="py-16 text-center">
          <h3 className="mb-2 text-xl font-extrabold text-rs-navy">No courses yet</h3>
          <p className="mb-6 text-rs-body">Create your first course to get started</p>
          <Button type="button" onClick={() => setShowCreateModal(true)}>
            Create Your First Course
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <Card key={course.id} className="overflow-hidden transition-shadow hover:shadow-md">
              <div className="aspect-video overflow-hidden bg-rs-navy">
                {course.thumbnailUrl ? (
                  <img src={course.thumbnailUrl} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-rs-muted">
                    No thumbnail
                  </div>
                )}
              </div>
              <div className="p-6">
                <div className="mb-4 flex items-start justify-between">
                  <Badge tone={course.status === 'PUBLISHED' ? 'success' : 'neutral'}>
                    {course.status}
                  </Badge>
                  <span className="text-sm font-semibold text-rs-muted">
                    {lessonCounts[course.id] ?? '—'} lessons
                  </span>
                </div>

                <h3 className="mb-2 text-xl font-extrabold text-rs-navy">{course.title}</h3>
                <p className="mb-4 line-clamp-2 text-sm text-rs-body">{course.description}</p>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/courses/${course.id}`)}
                  >
                    Manage
                  </Button>

                  {course.status === 'DRAFT' && (
                    <Button
                      type="button"
                      size="sm"
                      className="flex-1"
                      disabled={publishing === course.id}
                      onClick={() => handlePublish(course.id)}
                    >
                      {publishing === course.id ? 'Publishing...' : 'Publish'}
                    </Button>
                  )}

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={deleting === course.id}
                    className="!text-red-700 hover:!bg-red-50"
                    onClick={() => handleDelete(course.id)}
                  >
                    {deleting === course.id ? '...' : 'Delete'}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="max-w-md w-full p-6">
            <h2 className="mb-4 text-2xl font-extrabold text-rs-navy">Create New Course</h2>
            <form onSubmit={handleCreateCourse}>
              <Field
                label="Course Title *"
                value={newCourseTitle}
                onChange={(e) => setNewCourseTitle(e.target.value)}
                placeholder="e.g., Introduction to Python"
                required
              />
              <Field label="Description" className="mb-6">
                <textarea
                  value={newCourseDescription}
                  onChange={(e) => setNewCourseDescription(e.target.value)}
                  rows={3}
                  placeholder="Brief description of your course..."
                />
              </Field>
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  className="flex-1"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={creating || !newCourseTitle.trim()}
                >
                  {creating ? 'Creating...' : 'Create Course'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  )
}
