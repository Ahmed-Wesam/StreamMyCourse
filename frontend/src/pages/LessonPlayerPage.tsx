import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  enrollInCourse,
  getCourse,
  getCourseProgress,
  getPlaybackUrl,
  isEnrollmentRequiredError,
  isPlaybackAuthRequiredError,
  listLessons,
  updateLessonProgress,
  type Course,
  type CourseProgress,
  type Lesson,
} from '../lib/api'

// Progress tracking constants
const PROGRESS_INTERVAL_MS = 15000 // 15 seconds between heartbeat attempts
const MAX_CONSECUTIVE_FAILURES = 10 // Circuit breaker threshold
const MAX_SAME_POSITION_STREAK = 20 // Stop saving if timestamp doesn't change

function LessonItem({
  lesson,
  courseId,
  active,
  index,
  linkDisabled,
  completed,
}: {
  lesson: Lesson
  courseId: string
  active: boolean
  index: number
  linkDisabled: boolean
  completed?: boolean
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
      {!active && completed && (
        <div className="text-xs font-medium text-emerald-600">Done</div>
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
  const [searchParams] = useSearchParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])
  const lessonId = useMemo(() => params.lessonId ?? '', [params.lessonId])
  // Resume time from URL (?t=123) - saved position passed from CourseDetailPage
  const resumeTimeSec = useMemo(() => {
    const t = searchParams.get('t')
    if (!t) return null
    const parsed = parseInt(t, 10)
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null
  }, [searchParams])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsEnrollment, setNeedsEnrollment] = useState(false)
  const [needsSignIn, setNeedsSignIn] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [courseProgress, setCourseProgress] = useState<CourseProgress | null>(null)
  const lastAttemptRef = useRef<number>(0) // Track last attempt time (initialized to 0 to allow first update)
  const consecutiveFailuresRef = useRef<number>(0)
  const circuitOpenRef = useRef<boolean>(false)
  const lastSentPositionSecRef = useRef<number | null>(null)
  const samePositionStreakRef = useRef<number>(0)
  const samePositionCircuitOpenRef = useRef<boolean>(false)
  const inFlightProgressRef = useRef<Promise<unknown> | null>(null)
  const isUnmountedRef = useRef<boolean>(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  // Track if we've applied the initial resume time to prevent re-seeking
  const resumeAppliedRef = useRef<boolean>(false)
  // Track if we've sent duration update to prevent duplicate calls
  const durationSentRef = useRef<boolean>(false)

  const playbackNavLocked = needsEnrollment || needsSignIn

  useEffect(() => {
    return () => {
      isUnmountedRef.current = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function run() {
      setNeedsEnrollment(false)
      setNeedsSignIn(false)
      setSrc(null)
      try {
        const c = await getCourse(courseId)
        if (cancelled) return
        setCourse(c)
        const l = await listLessons(courseId)
        if (cancelled) return
        setLessons([...l].sort((a, b) => a.order - b.order))
        try {
          const pb = await getPlaybackUrl(courseId, lessonId)
          if (cancelled) return
          setSrc(pb.url)
          try {
            const prog = await getCourseProgress(courseId)
            if (!cancelled) setCourseProgress(prog)
          } catch {
            // Silently ignore expected progress errors (RDS unavailable, auth not configured)
          }
        } catch (inner) {
          if (cancelled) return
          if (isEnrollmentRequiredError(inner)) {
            setNeedsEnrollment(true)
            setSrc(null)
            setError(null)
          } else if (isPlaybackAuthRequiredError(inner)) {
            setNeedsSignIn(true)
            setSrc(null)
            setError(null)
          } else {
            setError(inner instanceof Error ? inner.message : 'Failed to load')
          }
        }
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load')
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

  const isLessonCompleted = useMemo(() => {
    const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
    return lessonProgress?.completed ?? false
  }, [courseProgress, lessonId])

  // Calculate the best resume time from URL param or saved progress
  const getResumeTimeSec = useCallback((): number => {
    // Prioritize URL param (passed from CourseDetailPage)
    if (resumeTimeSec != null && resumeTimeSec > 0) {
      return resumeTimeSec
    }
    // Fall back to saved progress from API
    const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
    const savedPosition = lessonProgress?.lastPositionSec ?? 0
    return savedPosition > 0 ? savedPosition : 0
  }, [resumeTimeSec, courseProgress, lessonId])

  // Handle video metadata loaded - set initial time if resuming, and send duration to backend
  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    // Send video duration to backend if we have a valid duration
    // This helps populate lesson duration for newly uploaded videos
    const videoDuration = Math.floor(video.duration)
    const activeLesson = lessons.find((l) => l.id === lessonId)
    const hasDuration = activeLesson?.duration && activeLesson.duration > 0

    if (videoDuration > 0 && !hasDuration && !durationSentRef.current) {
      // Mark as sent immediately to prevent duplicate calls
      durationSentRef.current = true
      // Send duration update (best effort - don't block playback on this)
      void updateLessonProgress(courseId, lessonId, {
        lastPositionSec: 0,
        durationSec: videoDuration,
      }).catch(() => {
        // Silently ignore - duration update is best effort
      })
    }

    if (resumeAppliedRef.current) return

    const resumeTime = getResumeTimeSec()
    if (resumeTime > 0 && resumeTime < video.duration) {
      video.currentTime = resumeTime
      resumeAppliedRef.current = true
    }
  }, [getResumeTimeSec, courseId, lessonId, lessons])

  // Reset flags when lesson changes
  useEffect(() => {
    resumeAppliedRef.current = false
    durationSentRef.current = false
  }, [lessonId])

  const coursePercentComplete = useMemo(() => {
    return courseProgress?.percentComplete ?? 0
  }, [courseProgress])

  // Helper to track and limit repeated saves at the same timestamp (e.g., user paused for hours)
  const shouldSkipBecauseSamePosition = (positionSec: number): boolean => {
    // If position changed, reset streak + close same-position circuit
    if (lastSentPositionSecRef.current === null || lastSentPositionSecRef.current !== positionSec) {
      lastSentPositionSecRef.current = positionSec
      samePositionStreakRef.current = 0
      samePositionCircuitOpenRef.current = false
      return false
    }

    // Position unchanged
    samePositionStreakRef.current += 1
    if (samePositionStreakRef.current >= MAX_SAME_POSITION_STREAK) {
      samePositionCircuitOpenRef.current = true
      return true
    }

    return false
  }

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget
    const now = Date.now()

    // Circuit breaker: stop if too many failures
    if (circuitOpenRef.current) return

    const positionSec = Math.floor(video.currentTime)
    if (samePositionCircuitOpenRef.current && lastSentPositionSecRef.current === positionSec) return

    // Throttle: 15 seconds between attempts
    if (now - lastAttemptRef.current < PROGRESS_INTERVAL_MS) return

    // Skip if already have in-flight request
    if (inFlightProgressRef.current) return

    const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lessonId)
    if (lessonProgress?.completed) return

    const activeLesson = lessons.find((l) => l.id === lessonId)
    const fromVideo =
      Number.isFinite(video.duration) && video.duration > 0 ? Math.floor(video.duration) : 0
    const durationSec = fromVideo > 0 ? fromVideo : (activeLesson?.duration ?? 0)

    // Record attempt time before sending
    lastAttemptRef.current = now

    if (shouldSkipBecauseSamePosition(positionSec)) return

    const promise = updateLessonProgress(courseId, lessonId, {
      lastPositionSec: positionSec,
      durationSec,
    })
    inFlightProgressRef.current = promise
    promise
      .then(() => {
        if (!isUnmountedRef.current) {
          // Reset failure count on success
          consecutiveFailuresRef.current = 0
        }
      })
      .catch(() => {
        // Count failures and trip circuit breaker if needed
        consecutiveFailuresRef.current++
        if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
          circuitOpenRef.current = true
        }
      })
      .finally(() => {
        inFlightProgressRef.current = null
      })
  }

  const handleVideoEnded = async () => {
    const activeLesson = lessons.find((l) => l.id === lessonId)
    if (!activeLesson) return

    // Circuit breaker check
    if (circuitOpenRef.current) return

    // Wait for any in-flight progress update
    if (inFlightProgressRef.current) {
      await inFlightProgressRef.current.catch(() => {}) // Ignore errors
    }

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: activeLesson.duration || 0,
        durationSec: activeLesson.duration || 0,
        markComplete: true,
      })
      // Reset failure count on success
      consecutiveFailuresRef.current = 0
      const prog = await getCourseProgress(courseId)
      if (!isUnmountedRef.current) {
        setCourseProgress(prog)
      }
    } catch {
      // Count failures and trip circuit breaker if needed
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }

  const handleMarkIncomplete = async () => {
    // Circuit breaker check
    if (circuitOpenRef.current) return

    const activeLesson = lessons.find((l) => l.id === lessonId)

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: 0,
        durationSec: activeLesson?.duration ?? 0,
        markIncomplete: true,
      })
      // Reset failure count on success
      consecutiveFailuresRef.current = 0
      const prog = await getCourseProgress(courseId)
      setCourseProgress(prog)
    } catch {
      // Count failures and trip circuit breaker if needed
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }

  // Checkpoint save helper (ignores throttle, respects circuit breaker)
  const saveCheckpoint = useCallback(async (positionSec: number) => {
    if (circuitOpenRef.current) return
    if (!courseId || !lessonId) return

    // Check same-position circuit breaker: prevents spam when user pauses and leaves
    // tab open for hours. After 20 saves at the same timestamp, we stop until
    // the position changes (user resumes playback).
    if (shouldSkipBecauseSamePosition(positionSec)) return

    const activeLesson = lessons.find((l) => l.id === lessonId)
    const durationSec = activeLesson?.duration ?? 0

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: positionSec,
        durationSec,
      })
      consecutiveFailuresRef.current = 0
    } catch {
      consecutiveFailuresRef.current++
      if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        circuitOpenRef.current = true
      }
    }
  }, [courseId, lessonId, lessons])

  // Video pause checkpoint
  const handlePause = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    saveCheckpoint(Math.floor(video.currentTime))
  }, [saveCheckpoint])

  // Visibility change checkpoint
  const handleVisibilityChange = useCallback(() => {
    if (document.hidden) {
      const video = videoRef.current
      if (!video) return
      saveCheckpoint(Math.floor(video.currentTime))
    }
  }, [saveCheckpoint])

  // Pagehide checkpoint - best effort save
  const handlePageHide = useCallback(() => {
    const video = videoRef.current
    if (!video || circuitOpenRef.current) return

    const positionSec = Math.floor(video.currentTime)

    // Best-effort save using checkpoint helper
    // Request may not complete if tab closes before fetch finishes
    saveCheckpoint(positionSec)
  }, [saveCheckpoint])

  // Checkpoint event listeners
  useEffect(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('pagehide', handlePageHide)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pagehide', handlePageHide)
    }
  }, [handleVisibilityChange, handlePageHide])

  return (
    <div>
      <div className="border-b border-slate-200/90 bg-slate-100">
        <div className="py-3">
          <div className="hidden min-h-[1.25rem] sm:block sm:pl-3">
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
        {needsSignIn && (
          <div className="mb-6 rounded-lg border border-sky-200 bg-sky-50 p-4">
            <h3 className="text-sm font-medium text-sky-900">Sign in to watch</h3>
            <p className="mt-1 text-sm text-sky-800">
              Sign in to your account to play this lesson and track your progress.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                to="/login"
                className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Sign in
              </Link>
              <Link
                to={`/courses/${courseId}`}
                className="inline-flex items-center rounded-lg border border-sky-300 bg-white px-4 py-2 text-sm font-medium text-sky-900 hover:bg-sky-100"
              >
                Course page
              </Link>
            </div>
          </div>
        )}

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
                      setNeedsSignIn(false)
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
                      if (isPlaybackAuthRequiredError(err)) {
                        setNeedsSignIn(true)
                        setNeedsEnrollment(false)
                        setSrc(null)
                        setError(null)
                      } else if (isEnrollmentRequiredError(err)) {
                        setNeedsEnrollment(true)
                        setNeedsSignIn(false)
                        setSrc(null)
                        setError(null)
                      } else {
                        setError(err instanceof Error ? err.message : 'Failed after enroll')
                      }
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
                  playsInline
                  preload="metadata"
                  crossOrigin="anonymous"
                  className="w-full aspect-video"
                  src={src || undefined}
                  onLoadedMetadata={handleLoadedMetadata}
                  onTimeUpdate={handleTimeUpdate}
                  onEnded={handleVideoEnded}
                  onPause={handlePause}
                />
              </div>
            )}

            {/* Lesson Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-bold text-gray-900">{activeLessonTitle}</h1>
                {isLessonCompleted && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                    Completed
                  </span>
                )}
              </div>

              {/* Course progress bar */}
              {courseProgress && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                    <span>Course Progress</span>
                    <span>{coursePercentComplete}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${coursePercentComplete}%` }}
                      role="progressbar"
                      aria-valuenow={coursePercentComplete}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                </div>
              )}

              <p className="mt-2 text-gray-600">
                {course?.description}
              </p>

              {/* Mark as not done button */}
              {isLessonCompleted && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={handleMarkIncomplete}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Mark as not done
                  </button>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="mt-6 flex items-center justify-between">
                {prevLesson ? (
                  playbackNavLocked ? (
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
                  playbackNavLocked ? (
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
                ) : !playbackNavLocked ? (
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
                {lessons.map((lesson, index) => {
                  const lessonProgress = courseProgress?.lessons.find((l) => l.lessonId === lesson.id)
                  return (
                    <LessonItem
                      key={lesson.id}
                      lesson={lesson}
                      courseId={courseId}
                      active={lesson.id === lessonId}
                      index={index}
                      linkDisabled={playbackNavLocked}
                      completed={lessonProgress?.completed}
                    />
                  )
                })}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}
