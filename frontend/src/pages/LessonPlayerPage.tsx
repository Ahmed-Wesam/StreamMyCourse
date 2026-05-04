import { useEffect, useMemo, useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  enrollInCourse,
  getCourse,
  getCoursePreview,
  getPlaybackUrl,
  isEnrollmentRequiredError,
  lessonPreviewsToStubLessons,
  listLessons,
  type Course,
  type Lesson,
} from '../lib/api'

function LessonItem({
  lesson,
  courseId,
  active,
  index,
  linkDisabled,
}: {
  lesson: Lesson
  courseId: string
  active: boolean
  index: number
  linkDisabled: boolean
}) {
  const rowClass = `group flex items-center px-4 py-3 transition-colors ${
    active
      ? 'bg-blue-50 border-l-4 border-blue-600'
      : linkDisabled
        ? 'cursor-default border-l-4 border-transparent opacity-80'
        : 'hover:bg-gray-50 border-l-4 border-transparent'
  }`
  const inner = (
    <>
      <div
        className={`relative h-8 w-8 shrink-0 overflow-hidden rounded-md flex items-center justify-center text-sm font-medium ${
          active
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-600 group-hover:bg-blue-100 group-hover:text-blue-600'
        } transition-colors`}
      >
        {!active && lesson.thumbnailUrl ? (
          <img src={lesson.thumbnailUrl} alt="" className="h-full w-full object-cover" />
        ) : active ? (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        ) : (
          index + 1
        )}
      </div>
      <div className="ml-3 flex-1">
        <h4 className={`text-sm font-medium ${active ? 'text-blue-900' : 'text-gray-900'}`}>
          {lesson.title}
        </h4>
        <p className="text-xs text-gray-500">Lesson {lesson.order}</p>
      </div>
      {active && !linkDisabled && (
        <div className="text-xs text-blue-600 font-medium">Playing</div>
      )}
      {linkDisabled && (
        <div className="text-xs font-medium text-amber-700">Locked</div>
      )}
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

function VideoSkeleton() {
  return (
    <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center animate-pulse">
      <div className="w-16 h-16 bg-gray-700 rounded-full" />
    </div>
  )
}

export default function LessonPlayerPage() {
  const params = useParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])
  const lessonId = useMemo(() => params.lessonId ?? '', [params.lessonId])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsEnrollment, setNeedsEnrollment] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    let cancelled = false

    async function run() {
      setNeedsEnrollment(false)
      setSrc(null)
      try {
        const c = await getCourse(courseId)
        if (cancelled) return
        setCourse(c)
        const [l, pb] = await Promise.all([
          listLessons(courseId),
          getPlaybackUrl(courseId, lessonId),
        ])
        if (cancelled) return
        setLessons([...l].sort((a, b) => a.order - b.order))
        setSrc(pb.url)
      } catch (e) {
        if (cancelled) return
        if (isEnrollmentRequiredError(e)) {
          setNeedsEnrollment(true)
          setError(null)
          try {
            const p = await getCoursePreview(courseId)
            if (!cancelled) {
              const { lessonsPreview: lp, ...courseFromPreview } = p
              setLessons(lessonPreviewsToStubLessons(lp))
              setCourse((prev) => prev ?? courseFromPreview)
            }
          } catch {
            if (!cancelled) setLessons([])
          }
        } else {
          setError(e instanceof Error ? e.message : 'Failed to load')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    if (courseId && lessonId) void run()

    return () => {
      cancelled = true
    }
  }, [courseId, lessonId])

  const activeLessonTitle = useMemo(() => {
    const l = lessons.find((x) => x.id === lessonId)
    return l?.title ?? 'Lesson'
  }, [lessons, lessonId])

  const activeLessonIndex = useMemo(() => {
    return lessons.findIndex((x) => x.id === lessonId)
  }, [lessons, lessonId])

  const nextLesson = useMemo(() => {
    if (activeLessonIndex < lessons.length - 1) {
      return lessons[activeLessonIndex + 1]
    }
    return null
  }, [lessons, activeLessonIndex])

  const prevLesson = useMemo(() => {
    if (activeLessonIndex > 0) {
      return lessons[activeLessonIndex - 1]
    }
    return null
  }, [lessons, activeLessonIndex])

  return (
    <div>
      <div className="border-b border-slate-200/90 bg-slate-100">
        <div className="py-3">
          <div className="hidden min-h-[1.25rem] sm:block">
            <Link
              to={`/courses/${courseId}`}
              className="text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              {course?.title ?? 'Course'}
            </Link>
            <span className="mx-2 text-gray-300">/</span>
            <span className="text-sm font-medium text-gray-900">{activeLessonTitle}</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="py-6">
        {needsEnrollment && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <h3 className="text-sm font-medium text-amber-900">Enroll to watch</h3>
            <p className="mt-1 text-sm text-amber-800">
              You need to enroll in this course before playback is available.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                disabled={enrolling}
                onClick={() => {
                  setEnrolling(true)
                  void (async () => {
                    try {
                      await enrollInCourse(courseId)
                      setNeedsEnrollment(false)
                      setLoading(true)
                      setError(null)
                      const c = await getCourse(courseId)
                      setCourse(c)
                      const [l, pb] = await Promise.all([
                        listLessons(courseId),
                        getPlaybackUrl(courseId, lessonId),
                      ])
                      setLessons([...l].sort((a, b) => a.order - b.order))
                      setSrc(pb.url)
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed after enroll')
                    } finally {
                      setEnrolling(false)
                      setLoading(false)
                    }
                  })()
                }}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {enrolling ? 'Enrolling…' : 'Enroll for free'}
              </button>
              <Link
                to={`/courses/${courseId}`}
                className="inline-flex items-center rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100"
              >
                Course page
              </Link>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 mb-6">
            <div className="flex">
              <svg className="w-5 h-5 text-red-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error loading video</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Player */}
          <div className="lg:col-span-2 space-y-4">
            {loading ? (
              <VideoSkeleton />
            ) : (
              <div className="rounded-xl overflow-hidden shadow-lg bg-black">
                <video 
                  ref={videoRef}
                  controls 
                  className="w-full aspect-video" 
                  src={src || undefined}
                />
              </div>
            )}

            {/* Lesson Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h1 className="text-2xl font-bold text-gray-900">{activeLessonTitle}</h1>
              <p className="mt-2 text-gray-600">
                {course?.description}
              </p>

              {/* Navigation Buttons */}
              <div className="mt-6 flex items-center justify-between">
                {prevLesson ? (
                  needsEnrollment ? (
                    <span className="inline-flex cursor-not-allowed items-center rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-400 opacity-60">
                      <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Previous
                    </span>
                  ) : (
                    <Link
                      to={`/courses/${courseId}/lessons/${prevLesson.id}`}
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Previous
                    </Link>
                  )
                ) : (
                  <div />
                )}

                {nextLesson ? (
                  needsEnrollment ? (
                    <span className="inline-flex cursor-not-allowed items-center rounded-lg bg-blue-400 px-4 py-2 text-sm font-medium text-white opacity-60">
                      Next
                      <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </span>
                  ) : (
                    <Link
                      to={`/courses/${courseId}/lessons/${nextLesson.id}`}
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Next
                      <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </Link>
                  )
                ) : !needsEnrollment ? (
                  <Link
                    to={`/courses/${courseId}`}
                    className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    Complete
                    <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </Link>
                ) : (
                  <Link
                    to={`/courses/${courseId}`}
                    className="inline-flex items-center rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Course page
                  </Link>
                )}
              </div>
            </div>
          </div>

          {/* Lessons Sidebar */}
          <aside className="lg:col-span-1">
            <div className="sticky top-28 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
              <div className="px-4 py-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900">Course Content</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'}
                </p>
              </div>
              <div className="divide-y divide-gray-100 max-h-[calc(100vh-300px)] overflow-y-auto">
                {lessons.map((lesson, index) => (
                  <LessonItem
                    key={lesson.id}
                    lesson={lesson}
                    courseId={courseId}
                    active={lesson.id === lessonId}
                    index={index}
                    linkDisabled={needsEnrollment}
                  />
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}
