import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from 'react'
import { Link, useParams, useSearchParams, type To } from 'react-router-dom'
import {
  enrollInCourse,
  getCourse,
  getCourseProgress,
  getPlaybackUrl,
  isEnrollmentRequiredError,
  isPlaybackAuthRequiredError,
  listLessons,
  listCourseModules,
  updateLessonProgress,
  type Course,
  type CourseModule,
  type CourseProgress,
  type Lesson,
} from '../lib/api'
import {
  catalogApiUserMessage,
  courseNotFoundMessage,
  incompleteLessonPlayerLinkMessage,
} from '../lib/apiUserMessages'
import { readMdUpMatch, useIsMdUp } from '../lib/useMediaQuery'
import { LessonPlayerMobileView } from './lesson-player/LessonPlayerMobileView'
import {
  CourseLessonsSidebar,
  resolveNextModuleQuizHref,
  resolvePrevModuleQuizHref,
  LessonPlaybackNavigation,
  LessonPlayerAlerts,
  LessonUpNextCard,
  sortLessonsByOrdering,
  sortModulesByOrder,
  VideoSkeleton,
} from './lesson-player/lessonPlayerUi'

// Progress tracking constants
const PROGRESS_INTERVAL_MS = 15000 // 15 seconds between heartbeat attempts
const MAX_CONSECUTIVE_FAILURES = 10 // Circuit breaker threshold
const MAX_SAME_POSITION_STREAK = 20 // Stop saving if timestamp doesn't change

function LessonPrimaryColumn({
  loading,
  src,
  videoRef,
  onLoadedMetadata,
  onTimeUpdate,
  onEnded,
  onPause,
  activeLessonTitle,
  activeModuleLabel,
  isLessonCompleted,
  courseDescription,
  onMarkComplete,
  onMarkIncomplete,
  courseId,
  prevLesson,
  prevQuizHref,
  nextLesson,
  nextQuizHref,
  playbackNavLocked,
}: {
  loading: boolean
  src: string | null
  videoRef: RefObject<HTMLVideoElement | null>
  onLoadedMetadata: () => void
  onTimeUpdate: (e: SyntheticEvent<HTMLVideoElement>) => void
  onEnded: () => void
  onPause: () => void
  activeLessonTitle: string
  activeModuleLabel: string
  isLessonCompleted: boolean
  courseDescription: string | undefined
  onMarkComplete: () => void
  onMarkIncomplete: () => void
  courseId: string
  prevLesson: Lesson | null
  prevQuizHref?: To | null
  nextLesson: Lesson | null
  nextQuizHref?: To | null
  playbackNavLocked: boolean
}) {
  const upNextTitle = nextQuizHref ? 'Module quiz' : nextLesson?.title
  const upNextDescription = nextQuizHref ? 'Continue to the module quiz' : 'Continue to the next lesson'

  return (
    <div className="lg:col-span-2 space-y-4">
      {loading ? (
        <VideoSkeleton />
      ) : (
        <div className="overflow-hidden rounded-xl bg-black shadow-md shadow-slate-900/10">
          <video
            ref={videoRef}
            controls
            playsInline
            preload="metadata"
            crossOrigin="anonymous"
            className="aspect-video w-full"
            src={src || undefined}
            onLoadedMetadata={onLoadedMetadata}
            onTimeUpdate={onTimeUpdate}
            onEnded={onEnded}
            onPause={onPause}
          />
        </div>
      )}

      <div className="rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-white to-blue-50/40 p-6 shadow-md shadow-slate-200/50 backdrop-blur-sm ring-1 ring-blue-50">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {activeModuleLabel ? (
              <div className="inline-flex max-w-full items-center rounded-full bg-gradient-to-r from-blue-50 to-slate-50 px-3 py-1 text-xs font-semibold text-blue-800 ring-1 ring-blue-100/80">
                <span className="truncate">{activeModuleLabel}</span>
              </div>
            ) : null}
            <h1 className="mt-1 bg-gradient-to-r from-slate-900 via-blue-900 to-slate-800 bg-clip-text text-2xl font-bold tracking-tight text-transparent">
              {activeLessonTitle}
            </h1>
          </div>

          <button
            type="button"
            disabled={loading || playbackNavLocked}
            onClick={isLessonCompleted ? onMarkIncomplete : onMarkComplete}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
              isLessonCompleted
                ? 'border border-slate-200 bg-slate-100 text-slate-700 shadow-sm hover:bg-slate-200/80'
                : 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md shadow-blue-900/10 hover:from-blue-700 hover:to-blue-800'
            }`}
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {isLessonCompleted ? 'Mark as Incomplete' : 'Mark as Complete'}
          </button>
        </div>

        {courseDescription ? (
          <p className="mt-2 text-slate-600">{courseDescription}</p>
        ) : null}

        {upNextTitle ? (
          <LessonUpNextCard
            upNextTitle={upNextTitle}
            upNextDescription={upNextDescription}
            playbackNavLocked={playbackNavLocked}
          />
        ) : null}

        <LessonPlaybackNavigation
          courseId={courseId}
          playbackNavLocked={playbackNavLocked}
          prevLesson={prevLesson}
          prevQuizHref={prevQuizHref}
          nextLesson={nextLesson}
          nextQuizHref={nextQuizHref}
        />
      </div>
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
  const [modules, setModules] = useState<CourseModule[]>([])
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
      setCourseProgress(null)
      try {
        const c = await getCourse(courseId)
        if (cancelled) return
        if (!c) {
          setError(courseNotFoundMessage)
          setCourse(null)
          setLessons([])
          setModules([])
          return
        }
        setCourse(c)
        const [l, m] = await Promise.all([listLessons(courseId), listCourseModules(courseId)])
        if (cancelled) return
        setModules(sortModulesByOrder(m))
        setLessons(sortLessonsByOrdering(l))
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
            setCourseProgress(null)
          } else if (isPlaybackAuthRequiredError(inner)) {
            setNeedsSignIn(true)
            setSrc(null)
            setError(null)
            setCourseProgress(null)
          } else {
            setCourseProgress(null)
            setError(catalogApiUserMessage(inner, 'loadLesson'))
          }
        }
      } catch (e) {
        if (cancelled) return
        setError(catalogApiUserMessage(e, 'loadLesson'))
        setCourse(null)
        setSrc(null)
        setLessons([])
        setModules([])
        setCourseProgress(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    if (!courseId || !lessonId) {
      setLoading(false)
      setError(incompleteLessonPlayerLinkMessage)
      return
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [courseId, lessonId])

  const activeLessonTitle = useMemo(() => {
    const l = lessons.find((x) => x.id === lessonId)
    return l?.title ?? 'Lesson'
  }, [lessons, lessonId])

  const activeModuleLabel = useMemo(() => {
    const activeLesson = lessons.find((x) => x.id === lessonId)
    if (!activeLesson) return ''
    const mod = modules.find((m) => m.id === activeLesson.moduleId)
    if (!mod) return ''
    return mod.title
  }, [lessons, lessonId, modules])

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

  const nextQuizHref = useMemo(
    () =>
      resolveNextModuleQuizHref({
        courseId,
        lessonId,
        lessons,
        modules,
        playbackNavLocked,
      }),
    [courseId, lessonId, lessons, modules, playbackNavLocked],
  )

  const prevQuizHref = useMemo(
    () =>
      resolvePrevModuleQuizHref({
        courseId,
        lessonId,
        lessons,
        modules,
        playbackNavLocked,
      }),
    [courseId, lessonId, lessons, modules, playbackNavLocked],
  )

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

  const handleTimeUpdate = (e: SyntheticEvent<HTMLVideoElement>) => {
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

  const handleMarkComplete = async () => {
    // Circuit breaker check
    if (circuitOpenRef.current) return

    const activeLesson = lessons.find((l) => l.id === lessonId)
    if (!activeLesson) return

    try {
      await updateLessonProgress(courseId, lessonId, {
        lastPositionSec: activeLesson.duration || 0,
        durationSec: activeLesson.duration || 0,
        markComplete: true,
      })
      consecutiveFailuresRef.current = 0
      // Optimistically reflect completion in UI immediately; refetch below is source of truth.
      setCourseProgress((prev) => {
        if (!prev) {
          const totalReadyLessons = lessons.length
          const completedCount = 1
          const percentComplete =
            totalReadyLessons > 0 ? Math.round((completedCount / totalReadyLessons) * 100) : 0
          return {
            courseId,
            totalReadyLessons,
            completedCount,
            percentComplete,
            lessons: lessons.map((l) => ({
              lessonId: l.id,
              completed: l.id === lessonId,
              lastPositionSec: l.id === lessonId ? (activeLesson.duration || 0) : 0,
            })),
          }
        }
        const nextLessons = prev.lessons.map((l) =>
          l.lessonId === lessonId ? { ...l, completed: true } : l,
        )
        const wasCompleted = prev.lessons.find((l) => l.lessonId === lessonId)?.completed ?? false
        const completedCount = wasCompleted ? prev.completedCount : prev.completedCount + 1
        const total = prev.totalReadyLessons > 0 ? prev.totalReadyLessons : nextLessons.length
        const percentComplete = total > 0 ? Math.round((completedCount / total) * 100) : prev.percentComplete
        return { ...prev, lessons: nextLessons, completedCount, percentComplete }
      })
      const prog = await getCourseProgress(courseId)
      if (!isUnmountedRef.current) {
        // Some backends are eventually consistent; keep the lesson marked complete if we've just done so.
        const existing = prog.lessons.find((l) => l.lessonId === lessonId)
        const ensuredLessons =
          existing == null
            ? [
                ...prog.lessons,
                { lessonId, completed: true, lastPositionSec: activeLesson.duration || 0 },
              ]
            : existing.completed
              ? prog.lessons
              : prog.lessons.map((l) =>
                  l.lessonId === lessonId ? { ...l, completed: true } : l,
                )
        const ensuredCompletedCount = Math.max(
          prog.completedCount,
          ensuredLessons.filter((l) => l.completed).length,
        )
        const total = prog.totalReadyLessons > 0 ? prog.totalReadyLessons : ensuredLessons.length
        const ensuredPercent = total > 0 ? Math.round((ensuredCompletedCount / total) * 100) : prog.percentComplete
        setCourseProgress({
          ...prog,
          lessons: ensuredLessons,
          completedCount: ensuredCompletedCount,
          percentComplete: ensuredPercent,
        })
      }
    } catch {
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

  const handleEnroll = useCallback(async () => {
    setEnrolling(true)
    try {
      await enrollInCourse(courseId)
      setNeedsEnrollment(false)
      setNeedsSignIn(false)
      setLoading(true)
      setError(null)
      const c = await getCourse(courseId)
      setCourse(c)
      const [l, m, pb] = await Promise.all([
        listLessons(courseId),
        listCourseModules(courseId),
        getPlaybackUrl(courseId, lessonId),
      ])
      setModules(sortModulesByOrder(m))
      setLessons(sortLessonsByOrdering(l))
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
        setError(catalogApiUserMessage(err, 'enroll'))
      }
    } finally {
      setEnrolling(false)
      setLoading(false)
    }
  }, [courseId, lessonId])

  const isMdUp = useIsMdUp()
  const [sidebarOpen, setSidebarOpen] = useState(readMdUpMatch)
  const desktopSidebarDismissedRef = useRef(false)
  const prevHeaderHref =
    prevQuizHref ?? (prevLesson ? `/courses/${courseId}/lessons/${prevLesson.id}` : null)
  const nextHeaderHref = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)

  useEffect(() => {
    if (isMdUp && !desktopSidebarDismissedRef.current) {
      setSidebarOpen(true)
    }
  }, [isMdUp])

  const openDesktopSidebar = useCallback(() => {
    desktopSidebarDismissedRef.current = false
    setSidebarOpen(true)
  }, [])

  const closeDesktopSidebar = useCallback(() => {
    desktopSidebarDismissedRef.current = true
    setSidebarOpen(false)
  }, [])

  if (!isMdUp) {
    return (
      <LessonPlayerMobileView
        courseId={courseId}
        lessons={lessons}
        modules={modules}
        lessonId={lessonId}
        activeLessonTitle={activeLessonTitle}
        activeModuleLabel={activeModuleLabel}
        loading={loading}
        src={src}
        videoRef={videoRef}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleVideoEnded}
        onPause={handlePause}
        needsSignIn={needsSignIn}
        needsEnrollment={needsEnrollment}
        enrolling={enrolling}
        error={error}
        onEnroll={() => void handleEnroll()}
        playbackNavLocked={playbackNavLocked}
        courseProgress={courseProgress}
        isLessonCompleted={isLessonCompleted}
        onMarkComplete={() => void handleMarkComplete()}
        onMarkIncomplete={() => void handleMarkIncomplete()}
        prevLesson={prevLesson}
        prevQuizHref={prevQuizHref}
        nextLesson={nextLesson}
        nextQuizHref={nextQuizHref}
      />
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)] bg-gradient-to-br from-slate-100 via-white to-blue-50/70">
      <CourseLessonsSidebar
        error={error}
        lessons={lessons}
        modules={modules}
        courseId={courseId}
        activeLessonId={lessonId}
        playbackNavLocked={playbackNavLocked}
        courseProgress={courseProgress}
        sidebarOpen={sidebarOpen}
        onClose={closeDesktopSidebar}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-col">
          <div
            className="h-1 w-full shrink-0 bg-gradient-to-r from-blue-400 via-blue-600 to-sky-500"
            aria-hidden
          />
          <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-gradient-to-r from-white via-white to-blue-50/60 px-4 py-3 shadow-sm shadow-slate-200/40">
          {!sidebarOpen ? (
            <button
              type="button"
              onClick={openDesktopSidebar}
              className="rounded-lg p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
              aria-label="Show sidebar"
              title="Show sidebar"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          ) : null}

          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium uppercase tracking-wide text-slate-500">
              <Link to={`/courses/${courseId}`} className="text-blue-700 hover:text-blue-800 hover:underline">
                {course?.title ?? 'Course'}
              </Link>
            </p>
            <p className="truncate text-sm font-semibold tracking-tight text-slate-900">
              {activeLessonTitle}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {prevHeaderHref ? (
              playbackNavLocked ? (
                <span className="inline-flex cursor-not-allowed items-center rounded-lg border border-slate-200 bg-slate-100 px-3 py-1.5 text-sm text-slate-400 opacity-90">
                  <svg className="mr-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Prev
                </span>
              ) : (
                <Link
                  to={prevHeaderHref}
                  className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-slate-50"
                >
                  <svg className="mr-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Prev
                </Link>
              )
            ) : null}

            {nextHeaderHref ? (
              playbackNavLocked ? (
                <span className="inline-flex cursor-not-allowed items-center rounded-lg border border-slate-200 bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-400 opacity-90">
                  Next
                  <svg className="ml-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              ) : (
                <Link
                  to={nextHeaderHref}
                  className="inline-flex items-center rounded-md bg-gradient-to-r from-blue-600 to-blue-700 px-3 py-1.5 text-sm font-semibold text-white shadow-md shadow-blue-900/10 transition-all hover:from-blue-700 hover:to-blue-800"
                >
                  Next
                  <svg className="ml-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              )
            ) : null}
          </div>
        </div>
        </div>

        <div className="bg-gradient-to-b from-transparent via-white/50 to-blue-50/30">
          <main className="mx-auto max-w-4xl px-6 py-8">
            <LessonPlayerAlerts
              needsSignIn={needsSignIn}
              needsEnrollment={needsEnrollment}
              enrolling={enrolling}
              error={error}
              courseId={courseId}
              onEnroll={handleEnroll}
            />

            <LessonPrimaryColumn
              loading={loading}
              src={src}
              videoRef={videoRef}
              onLoadedMetadata={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleVideoEnded}
              onPause={handlePause}
              activeLessonTitle={activeLessonTitle}
              activeModuleLabel={activeModuleLabel}
              isLessonCompleted={isLessonCompleted}
              courseDescription={course?.description}
              onMarkComplete={() => void handleMarkComplete()}
              onMarkIncomplete={() => void handleMarkIncomplete()}
              courseId={courseId}
              prevLesson={prevLesson}
              prevQuizHref={prevQuizHref}
              nextLesson={nextLesson}
              nextQuizHref={nextQuizHref}
              playbackNavLocked={playbackNavLocked}
            />
          </main>
        </div>
      </div>
    </div>
  )
}
