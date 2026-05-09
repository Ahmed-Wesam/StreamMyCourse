import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
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
import { groupLessonsByModule } from '../lib/lessonGrouping'

// Progress tracking constants
const PROGRESS_INTERVAL_MS = 15000 // 15 seconds between heartbeat attempts
const MAX_CONSECUTIVE_FAILURES = 10 // Circuit breaker threshold
const MAX_SAME_POSITION_STREAK = 20 // Stop saving if timestamp doesn't change

function formatDurationMmSs(durationSec: number | undefined): string {
  if (!durationSec || durationSec <= 0) return ''
  const total = Math.round(durationSec)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function LessonItem({
  lesson,
  courseId,
  active,
  linkDisabled,
  completed,
  progressPct,
  durationLabel,
}: {
  lesson: Lesson
  courseId: string
  active: boolean
  linkDisabled: boolean
  completed?: boolean
  progressPct?: number
  durationLabel?: string
}) {
  const rowClass = `group flex items-start px-4 py-3 transition-colors ${
    active
      ? 'bg-blue-50 border-l-4 border-blue-600'
      : linkDisabled
        ? 'cursor-default border-l-4 border-transparent opacity-80'
        : 'hover:bg-gray-50 border-l-4 border-transparent'
  }`
  const inner = (
    <>
      <div className="mt-0.5 h-6 w-6 shrink-0 flex items-center justify-center text-muted-foreground">
        {linkDisabled ? (
          <>
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M7 10V8a5 5 0 0 1 10 0v2"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <path
                d="M7 10h10v10H7V10Z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            </svg>
            <span className="sr-only">Locked</span>
          </>
        ) : active ? (
          <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8 5v14l11-7z" />
          </svg>
        ) : (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M8 5v14l11-7z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
          </svg>
        )}
      </div>

      <div className="ml-3 flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <h4 className={`text-sm truncate ${active ? 'text-blue-900 font-semibold' : 'text-gray-900 font-medium'}`}>
            {lesson.title}
          </h4>
          <div className="shrink-0 flex items-center justify-end gap-3 pl-2">
            {durationLabel ? <div className="text-xs text-muted-foreground tabular-nums">{durationLabel}</div> : null}
            {!active && completed ? (
              <div className="pt-0.5">
                <span className="sr-only">Completed lesson</span>
                <svg
                  className="h-4 w-4 text-emerald-600"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-label="Completed lesson"
                >
                  <path
                    d="M20 6 9 17l-5-5"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            ) : null}
          </div>
        </div>
        {progressPct != null ? (
          <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden" aria-label="Lesson progress">
            <div
              className="h-full overflow-hidden transition-[width] duration-300 rounded-full"
              style={{ width: `${progressPct}%` }}
            >
              <div
                className="h-full w-full"
                style={{
                  backgroundImage:
                    'linear-gradient(90deg, rgb(37 99 235), rgb(124 58 237), rgb(236 72 153), rgb(245 158 11), rgb(34 197 94))',
                }}
              />
            </div>
          </div>
        ) : null}
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

function VideoSkeleton() {
  return (
    <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center animate-pulse">
      <div className="w-16 h-16 bg-gray-700 rounded-full" />
    </div>
  )
}

function sortModulesByOrder(modules: CourseModule[]) {
  return [...modules].sort((a, b) => a.order - b.order)
}

function sortLessonsByOrdering(lessons: Lesson[]) {
  return [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)
}

function LessonPlayerAlerts({
  needsSignIn,
  needsEnrollment,
  enrolling,
  error,
  courseId,
  onEnroll,
}: {
  needsSignIn: boolean
  needsEnrollment: boolean
  enrolling: boolean
  error: string | null
  courseId: string
  onEnroll: () => void
}) {
  return (
    <>
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
              onClick={onEnroll}
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
    </>
  )
}

function LessonPlaybackNavigation({
  courseId,
  playbackNavLocked,
  prevLesson,
  nextLesson,
}: {
  courseId: string
  playbackNavLocked: boolean
  prevLesson: Lesson | null
  nextLesson: Lesson | null
}) {
  const prevLeft =
    prevLesson == null ? (
      <div />
    ) : playbackNavLocked ? (
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

  const nextLockedMarkup = (
    <span className="inline-flex cursor-not-allowed items-center rounded-lg bg-blue-400 px-4 py-2 text-sm font-medium text-white opacity-60">
      Next
      <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </span>
  )

  const coursePageMarkup = (
    <Link
      to={`/courses/${courseId}`}
      className="inline-flex items-center rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
    >
      Course page
    </Link>
  )

  const nextRight =
    nextLesson != null ? (
      playbackNavLocked ? (
        nextLockedMarkup
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
    ) : playbackNavLocked ? (
      coursePageMarkup
    ) : (
      <div />
    )

  return (
    <div className="mt-6 flex items-center justify-between">
      {prevLeft}
      {nextRight}
    </div>
  )
}

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
  nextLesson,
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
  nextLesson: Lesson | null
  playbackNavLocked: boolean
}) {
  return (
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
            onLoadedMetadata={onLoadedMetadata}
            onTimeUpdate={onTimeUpdate}
            onEnded={onEnded}
            onPause={onPause}
          />
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {activeModuleLabel ? (
              <div className="inline-flex max-w-full items-center rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-700">
                <span className="truncate">{activeModuleLabel}</span>
              </div>
            ) : null}
            <h1 className="mt-1 text-2xl font-bold text-gray-900">{activeLessonTitle}</h1>
          </div>

          <button
            type="button"
            disabled={loading || playbackNavLocked}
            onClick={isLessonCompleted ? onMarkIncomplete : onMarkComplete}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed ${
              isLessonCompleted ? 'bg-slate-600 hover:bg-slate-700' : 'bg-primary hover:bg-blue-700'
            }`}
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {isLessonCompleted ? 'Mark as Incomplete' : 'Mark as Complete'}
          </button>
        </div>

        <p className="mt-2 text-gray-600">{courseDescription}</p>

        {nextLesson && (
          <div className="mt-5 rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 h-9 w-9 shrink-0 rounded-lg bg-white border border-gray-200 flex items-center justify-center text-gray-500">
                {playbackNavLocked ? (
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M7 10V8a5 5 0 0 1 10 0v2"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <path
                      d="M7 10h10v10H7V10Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Up next</div>
                <div className="mt-1 text-sm font-semibold text-gray-900 truncate">{nextLesson.title}</div>
                <div className="mt-0.5 text-xs text-gray-500">
                  {playbackNavLocked ? 'Complete this lesson to unlock' : 'Continue to the next lesson'}
                </div>
              </div>
            </div>
          </div>
        )}

        <LessonPlaybackNavigation
          courseId={courseId}
          playbackNavLocked={playbackNavLocked}
          prevLesson={prevLesson}
          nextLesson={nextLesson}
        />
      </div>
    </div>
  )
}

function CourseLessonsSidebar({
  error,
  lessons,
  modules,
  courseId,
  activeLessonId,
  playbackNavLocked,
  courseProgress,
  sidebarOpen,
  onClose,
}: {
  error: string | null
  lessons: Lesson[]
  modules: CourseModule[]
  courseId: string
  activeLessonId: string
  playbackNavLocked: boolean
  courseProgress: CourseProgress | null
  sidebarOpen: boolean
  onClose: () => void
}) {
  const sections = useMemo(
    () => groupLessonsByModule(lessons, modules).filter((s) => s.lessons.length > 0),
    [lessons, modules],
  )
  const percent = courseProgress?.percentComplete ?? 0
  const completed = courseProgress?.completedCount ?? 0
  const total = courseProgress?.totalReadyLessons ?? lessons.length

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})

  useEffect(() => {
    setOpenSections((prev) => {
      // Preserve manual toggles, but ensure we have keys for all sections.
      const next = { ...prev }
      for (const section of sections) {
        if (next[section.id] === undefined) next[section.id] = true
      }
      // When playback navigation is locked, keep everything expanded so the user can see locked items.
      if (playbackNavLocked) {
        for (const section of sections) next[section.id] = true
        return next
      }
      return next
    })
  }, [sections, activeLessonId, playbackNavLocked])

  return (
    <aside
      className={`${sidebarOpen ? 'w-80' : 'w-0'} shrink-0 transition-all duration-300 overflow-hidden border-r border-border bg-card flex flex-col`}
      aria-label="Course sidebar"
    >
      <div className="p-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">
              Course Progress
            </p>
            <p className="text-xs text-muted-foreground">
              {completed} of {total} lessons completed
            </p>
          </div>
          <button
            type="button"
            className="md:hidden p-2 rounded-md hover:bg-muted/50 text-muted-foreground"
            aria-label="Close sidebar"
            onClick={onClose}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${percent}%` }} />
          </div>
          <span className="text-xs text-muted-foreground shrink-0">{percent}%</span>
        </div>
      </div>

      {!error && (
        <div className="flex-1 overflow-y-auto">
          {sections.map((section) => {
            const expanded = playbackNavLocked ? true : Boolean(openSections[section.id])
            return (
              <div key={section.id}>
                <button
                  type="button"
                  className="w-full rounded-lg border border-border bg-white px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground flex items-center justify-between hover:bg-muted/30 transition-colors"
                  aria-expanded={expanded}
                  onClick={() =>
                    setOpenSections((s) => ({ ...s, [section.id]: !s[section.id] }))
                  }
                >
                  <span>{section.title}</span>
                  <svg
                    className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M6 9l6 6 6-6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>

                {expanded ? (
                  <div>
                    {section.lessons.map((lesson) => {
                      const lessonProgressEntry = courseProgress?.lessons.find((l) => l.lessonId === lesson.id)
                      const durationSec = lesson.duration ?? 0
                      const rawPct =
                        durationSec > 0
                          ? Math.round(((lessonProgressEntry?.lastPositionSec ?? 0) / durationSec) * 100)
                          : 0
                      const progressPct = lessonProgressEntry?.completed
                        ? 100
                        : durationSec > 0
                          ? Math.max(0, Math.min(99, rawPct))
                          : undefined
                      return (
                        <LessonItem
                          key={lesson.id}
                          lesson={lesson}
                          courseId={courseId}
                          active={lesson.id === activeLessonId}
                          linkDisabled={playbackNavLocked}
                          completed={lessonProgressEntry?.completed}
                          progressPct={progressPct}
                          durationLabel={formatDurationMmSs(lesson.duration)}
                        />
                      )
                    })}
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </aside>
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
          setError('Course not found')
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
            setError(inner instanceof Error ? inner.message : 'Failed to load')
          }
        }
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load')
        setCourse(null)
        setSrc(null)
        setLessons([])
        setModules([])
        setCourseProgress(null)
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
        setError(err instanceof Error ? err.message : 'Failed after enroll')
      }
    } finally {
      setEnrolling(false)
      setLoading(false)
    }
  }, [courseId, lessonId])

  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-background">
      <CourseLessonsSidebar
        error={error}
        lessons={lessons}
        modules={modules}
        courseId={courseId}
        activeLessonId={lessonId}
        playbackNavLocked={playbackNavLocked}
        courseProgress={courseProgress}
        sidebarOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-white shrink-0">
          <button
            type="button"
            onClick={() => setSidebarOpen((s) => !s)}
            className="p-2 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground"
            aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>

          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground truncate">
              <Link to={`/courses/${courseId}`} className="hover:underline">
                {course?.title ?? 'Course'}
              </Link>
            </p>
            <p className="text-sm truncate" style={{ fontWeight: 600 }}>
              {activeLessonTitle}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {prevLesson ? (
              playbackNavLocked ? (
                <span className="inline-flex cursor-not-allowed items-center rounded-md border border-border bg-muted px-3 py-1.5 text-sm text-muted-foreground opacity-60">
                  <svg className="mr-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Prev
                </span>
              ) : (
                <Link
                  to={`/courses/${courseId}/lessons/${prevLesson.id}`}
                  className="inline-flex items-center rounded-md border border-border bg-white px-3 py-1.5 text-sm hover:bg-muted/40 transition-colors"
                >
                  <svg className="mr-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Prev
                </Link>
              )
            ) : null}

            {nextLesson ? (
              playbackNavLocked ? (
                <span className="inline-flex cursor-not-allowed items-center rounded-md bg-primary px-3 py-1.5 text-sm text-white opacity-60">
                  Next
                  <svg className="ml-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              ) : (
                <Link
                  to={`/courses/${courseId}/lessons/${nextLesson.id}`}
                  className="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm text-white hover:bg-blue-700 transition-colors"
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

        <div className="flex-1 overflow-y-auto">
          <main className="max-w-4xl mx-auto px-6 py-8">
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
              nextLesson={nextLesson}
              playbackNavLocked={playbackNavLocked}
            />
          </main>
        </div>
      </div>
    </div>
  )
}
