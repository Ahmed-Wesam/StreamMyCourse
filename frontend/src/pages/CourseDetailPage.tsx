import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  enrollInCourse,
  getCourse,
  getCoursePreview,
  hasSignedInIdToken,
  isEnrollmentRequiredError,
  lessonPreviewsToStubLessons,
  listLessons,
  type Course,
  type Lesson,
} from '../lib/api'

function SkeletonLesson() {
  return (
    <div className="flex items-center px-6 py-4 animate-pulse">
      <div className="w-10 h-10 bg-gray-200 rounded-full" />
      <div className="ml-4 flex-1">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
        <div className="h-3 bg-gray-200 rounded w-1/4" />
      </div>
    </div>
  )
}

function CourseDetailHero({
  loading,
  course,
  lessons,
}: {
  loading: boolean
  course: Course | null
  lessons: Lesson[]
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-600/40 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950/90 text-white shadow-xl shadow-slate-900/20 ring-1 ring-white/10 lg:rounded-3xl">
      <div className="px-5 py-10 sm:px-8 lg:px-10 lg:py-14">
        <Link
          to="/"
          className="mb-6 inline-flex items-center text-sm text-slate-300 transition-colors hover:text-white"
        >
          <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to all courses
        </Link>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-x-14">
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">{loading ? 'Loading…' : course?.title}</h1>
            <p className="mt-4 max-w-2xl text-lg text-slate-300">
              {loading ? '' : course?.description}
            </p>
            {!loading && course && (
              <div className="mt-6">
                <span className="rounded-full bg-white/15 px-3 py-1 text-sm backdrop-blur-sm">
                  {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'}
                </span>
              </div>
            )}
          </div>
          <div className="flex justify-center lg:justify-end">
            <div className="aspect-video w-full max-w-lg overflow-hidden rounded-xl border border-slate-600/80 bg-slate-900 shadow-lg">
              {!loading && course?.thumbnailUrl ? (
                <img src={course.thumbnailUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-slate-500">
                  <span className="text-sm">Course preview</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function CourseDetailBody({
  courseId,
  error,
  loading,
  lessons,
  course,
  previewOnly,
  needsEnrollment,
  enrolling,
  onEnroll,
}: {
  courseId: string
  error: string | null
  loading: boolean
  lessons: Lesson[]
  course: Course | null
  previewOnly: boolean
  needsEnrollment: boolean
  enrolling: boolean
  onEnroll: () => void
}) {
  return (
    <div className="space-y-8 py-6 sm:py-8">
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex">
            <svg className="mt-0.5 h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading course</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-4">
            <div className="h-6 w-24 animate-pulse rounded bg-gray-200" />
          </div>
          <SkeletonLesson />
          <SkeletonLesson />
          <SkeletonLesson />
        </div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
              <div className="border-b border-gray-100 px-6 py-4">
                <h2 className="text-lg font-semibold text-gray-900">Course Content</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'}
                </p>
              </div>
              <div className="divide-y divide-gray-100">
                {lessons.map((lesson, index) => (
                  <LessonItem
                    key={lesson.id}
                    lesson={lesson}
                    courseId={courseId}
                    index={index}
                    linkDisabled={previewOnly || needsEnrollment}
                  />
                ))}
              </div>
              {lessons.length === 0 && (
                <div className="px-6 py-12 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
                    <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <h3 className="font-medium text-gray-900">No lessons yet</h3>
                  <p className="mt-1 text-sm text-gray-500">This course doesn't have any lessons.</p>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-28 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
              <h3 className="mb-4 font-semibold text-gray-900">About this course</h3>
              <p className="text-sm text-gray-600">{course?.description || 'No description available.'}</p>
              <div className="mt-6 space-y-3 border-t border-gray-100 pt-6">
                {needsEnrollment && (
                  <button
                    type="button"
                    onClick={() => void onEnroll()}
                    disabled={enrolling}
                    className="inline-flex w-full items-center justify-center rounded-lg bg-emerald-600 px-4 py-3 font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {enrolling ? 'Enrolling…' : 'Enroll for free'}
                  </button>
                )}
                {previewOnly && (
                  <p className="text-center text-sm text-gray-600">
                    <Link to="/login" className="font-medium text-blue-600 hover:text-blue-800">
                      Sign in
                    </Link>{' '}
                    to enroll and watch lessons.
                  </p>
                )}
                <Link
                  to={`/courses/${courseId}/lessons/${lessons[0]?.id}`}
                  className={`inline-flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 ${
                    lessons.length === 0 || previewOnly || needsEnrollment
                      ? 'pointer-events-none cursor-not-allowed opacity-50'
                      : ''
                  }`}
                >
                  <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  {lessons.length > 0 ? 'Start Learning' : 'No lessons'}
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function LessonItem({
  lesson,
  courseId,
  index,
  linkDisabled,
}: {
  lesson: Lesson
  courseId: string
  index: number
  linkDisabled: boolean
}) {
  const rowClass =
    'group flex items-center px-6 py-4 border-b border-gray-100 last:border-0 ' +
    (linkDisabled ? 'cursor-default opacity-80' : 'cursor-pointer hover:bg-blue-50 transition-colors')
  const inner = (
    <>
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg bg-blue-100 text-blue-600">
        {lesson.thumbnailUrl ? (
          <img src={lesson.thumbnailUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-sm font-semibold group-hover:bg-blue-600 group-hover:text-white transition-colors">
            {index + 1}
          </span>
        )}
      </div>
      <div className="ml-4 flex-1">
        <h3 className="text-gray-900 font-medium group-hover:text-blue-700 transition-colors">
          {lesson.title}
        </h3>
        <p className="text-sm text-gray-500">Lesson {lesson.order}</p>
      </div>
      <div className="flex items-center text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-sm font-medium mr-2">{linkDisabled ? 'Locked' : 'Play'}</span>
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    </>
  )
  if (linkDisabled) {
    return <div className={rowClass}>{inner}</div>
  }
  return (
    <Link to={`/courses/${courseId}/lessons/${lesson.id}`} className={rowClass}>
      {inner}
    </Link>
  )
}

export default function CourseDetailPage() {
  const params = useParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [previewOnly, setPreviewOnly] = useState(false)
  const [needsEnrollment, setNeedsEnrollment] = useState(false)
  const [enrolling, setEnrolling] = useState(false)

  const loadCourseData = useCallback(async () => {
    setError(null)
    setLoading(true)
    setPreviewOnly(false)
    setNeedsEnrollment(false)
    const signedIn = await hasSignedInIdToken()
    try {
      if (!signedIn) {
        const p = await getCoursePreview(courseId)
        const { lessonsPreview: lp, ...rest } = p
        setCourse(rest)
        setLessons(lessonPreviewsToStubLessons(lp))
        setPreviewOnly(true)
        return
      }
      const c = await getCourse(courseId)
      setCourse(c)
      try {
        const l = await listLessons(courseId)
        setLessons([...l].sort((a, b) => a.order - b.order))
        setNeedsEnrollment(false)
      } catch (inner) {
        if (isEnrollmentRequiredError(inner)) {
          try {
            const p = await getCoursePreview(courseId)
            setLessons(lessonPreviewsToStubLessons(p.lessonsPreview))
          } catch {
            setLessons([])
          }
          setNeedsEnrollment(true)
        } else {
          throw inner
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    if (courseId) void loadCourseData()
  }, [courseId, loadCourseData])

  const onEnroll = useCallback(async () => {
    if (!courseId) return
    setEnrolling(true)
    setError(null)
    try {
      await enrollInCourse(courseId)
      await loadCourseData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enrollment failed')
    } finally {
      setEnrolling(false)
    }
  }, [courseId, loadCourseData])

  return (
    <div className="space-y-6 sm:space-y-8">
        <CourseDetailHero loading={loading} course={course} lessons={lessons} />
        <CourseDetailBody
          courseId={courseId}
          error={error}
          loading={loading}
          lessons={lessons}
          course={course}
          previewOnly={previewOnly}
          needsEnrollment={needsEnrollment}
          enrolling={enrolling}
          onEnroll={onEnroll}
        />
    </div>
  )
}
