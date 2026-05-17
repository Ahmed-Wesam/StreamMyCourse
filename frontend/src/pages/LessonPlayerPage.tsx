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
import { groupLessonsByModule } from '../lib/lessonGrouping'
import { lessonPlayerPath, moduleQuizLinkTo } from '../lib/moduleQuizNavigation'

// Progress tracking constants
const PROGRESS_INTERVAL_MS = 15000 // 15 seconds between heartbeat attempts
const MAX_CONSECUTIVE_FAILURES = 10 // Circuit breaker threshold
const MAX_SAME_POSITION_STREAK = 20 // Stop saving if timestamp doesn't change

/** Progress fills — layered blues (professional). */
const PRO_BLUE_STRIP =
  'linear-gradient(90deg, #bfdbfe, #93c5fd, #60a5fa, #3b82f6, #2563eb, #60a5fa)'
/** Compact chrome (e.g. Up next icon shell) — white through sky into blue. */
const PRO_BLUE_FRAME =
  'linear-gradient(155deg, #ffffff, #eff6ff, #dbeafe, #93c5fd, #60a5fa)'

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
      ? 'border-l-[3px] border-blue-600 bg-gradient-to-r from-blue-50 to-white shadow-sm'
      : linkDisabled
        ? 'cursor-default border-l-4 border-transparent opacity-80'
        : 'border-l-4 border-transparent hover:bg-slate-50'
  }`
  const inner = (
    <>
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center text-slate-400">
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
          <svg className="h-4 w-4 text-blue-600" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
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
          <h4
            className={`text-sm truncate ${active ? 'font-semibold text-slate-900' : 'font-medium text-slate-600'}`}
          >
            {lesson.title}
          </h4>
          <div className="shrink-0 flex items-center justify-end gap-3 pl-2">
            {durationLabel ? (
              <div className="text-xs tabular-nums tracking-wider text-slate-600">{durationLabel}</div>
            ) : null}
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
          <div
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200/80"
            aria-label="Lesson progress"
          >
            <div
              className="h-full overflow-hidden transition-[width] duration-300 rounded-full"
              style={{ width: `${progressPct}%` }}
            >
              <div
                className="h-full w-full"
                style={{ backgroundImage: PRO_BLUE_STRIP }}
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
    <div className="flex aspect-video animate-pulse items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-slate-100 to-slate-200/90 shadow-sm">
      <div className="h-14 w-14 rounded-full bg-slate-300/50" />
    </div>
  )
}

function sortModulesByOrder(modules: CourseModule[]) {
  return [...modules].sort((a, b) => a.order - b.order)
}

function sortLessonsByOrdering(lessons: Lesson[]) {
  return [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)
}

function hasAvailableModuleQuiz(
  module: CourseModule | undefined,
): module is CourseModule & { moduleQuiz: { available: true; servedCountN: number } } {
  return module?.moduleQuiz?.available === true
}

function ModuleQuizItem({
  courseId,
  module,
  sectionLessons,
  activeLessonId,
}: {
  courseId: string
  module: CourseModule
  sectionLessons: Lesson[]
  activeLessonId: string
}) {
  const servedCount = module.moduleQuiz?.servedCountN
  const latestScorePercent = module.moduleQuiz?.latestScorePercent
  const returnLesson =
    sectionLessons.find((lesson) => lesson.id === activeLessonId) ??
    sectionLessons[sectionLessons.length - 1]
  const quizTo =
    returnLesson != null
      ? moduleQuizLinkTo(courseId, module.id, lessonPlayerPath(courseId, returnLesson.id))
      : `/courses/${courseId}/modules/${module.id}/quiz`

  return (
    <Link
      to={quizTo}
      className="group flex items-start border-l-4 border-transparent px-4 py-3 transition-colors hover:bg-slate-50"
    >
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center text-blue-600">
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M8 5h8M8 9h8M8 13h5M6 3h12a1 1 0 0 1 1 1v16l-3-2-3 2-3-2-3 2V4a1 1 0 0 1 1-1Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <div className="ml-3 flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <h4 className="truncate text-sm font-medium text-slate-600">Module quiz</h4>
          <div className="flex shrink-0 flex-col items-end gap-0.5">
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-100">
              Quiz
            </span>
            {latestScorePercent != null ? (
              <span className="text-[11px] font-medium text-slate-500">{latestScorePercent}%</span>
            ) : null}
          </div>
        </div>
        <p className="mt-0.5 truncate text-xs text-slate-500">
          {servedCount ? `${servedCount} questions` : 'Quiz'}
        </p>
      </div>
    </Link>
  )
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
        <div className="mb-6 rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-white to-blue-50/50 p-5 shadow-sm shadow-slate-200/60 ring-1 ring-blue-100/80">
          <h3 className="text-sm font-semibold text-slate-900">Sign in to watch</h3>
          <p className="mt-1 text-sm text-slate-600">
            Sign in to your account to play this lesson and track your progress.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              to="/login"
              className="inline-flex items-center rounded-lg bg-gradient-to-r from-blue-600 via-blue-600 to-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-900/15 transition-all hover:from-blue-700 hover:to-blue-800"
            >
              Sign in
            </Link>
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/60"
            >
              Course page
            </Link>
          </div>
        </div>
      )}

      {needsEnrollment && (
        <div className="mb-6 rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-blue-50/30 to-slate-50/80 p-5 shadow-sm shadow-slate-200/60 ring-1 ring-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">Enroll to watch</h3>
          <p className="mt-1 text-sm text-slate-600">
            You need to enroll in this course before playback is available.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={enrolling}
              onClick={onEnroll}
              className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-900/15 transition-all hover:from-blue-700 hover:to-blue-800 disabled:opacity-60"
            >
              {enrolling ? 'Enrolling…' : 'Enroll for free'}
            </button>
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/60"
            >
              Course page
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50/80 p-4 shadow-sm">
          <div className="flex">
            <svg className="mt-0.5 h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-red-900">Error loading video</h3>
              <p className="mt-1 text-sm text-red-800/90">{error}</p>
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
  nextQuizHref,
}: {
  courseId: string
  playbackNavLocked: boolean
  prevLesson: Lesson | null
  nextLesson: Lesson | null
  nextQuizHref?: To | null
}) {
  const prevLeft =
    prevLesson == null ? (
      <div />
    ) : playbackNavLocked ? (
      <span className="inline-flex cursor-not-allowed items-center rounded-lg border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-400 opacity-90">
        <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Previous
      </span>
    ) : (
      <Link
        to={`/courses/${courseId}/lessons/${prevLesson.id}`}
        className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-blue-200 hover:bg-slate-50"
      >
        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Previous
      </Link>
    )

  const nextLockedMarkup = (
    <span className="inline-flex cursor-not-allowed items-center rounded-lg border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-400 opacity-80">
      Next
      <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </span>
  )

  const coursePageMarkup = (
    <Link
      to={`/courses/${courseId}`}
      className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-slate-50"
    >
      Course page
    </Link>
  )

  const nextHref = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)

  const nextRight =
    nextHref != null ? (
      playbackNavLocked ? (
        nextLockedMarkup
      ) : (
        <Link
          to={nextHref}
          className="inline-flex items-center rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-900/10 transition-all hover:from-blue-700 hover:to-blue-800"
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

        <p className="mt-2 text-slate-600">{courseDescription}</p>

        {upNextTitle && (
          <div className="mt-5 rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50/90 to-blue-50/50 p-4 shadow-sm">
            <div className="flex items-start gap-3">
              <div
                className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl p-0.5 text-white shadow-md"
                style={{ background: PRO_BLUE_FRAME }}
              >
                <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-white text-blue-600 ring-1 ring-slate-200">
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
              </div>
              <div className="min-w-0">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-blue-600/90">
                  Up next
                </div>
                <div className="mt-1 truncate text-sm font-semibold text-slate-900">{upNextTitle}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {playbackNavLocked ? 'Complete this lesson to unlock' : upNextDescription}
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
          nextQuizHref={nextQuizHref}
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
    () => groupLessonsByModule(lessons, modules),
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
      className={`${sidebarOpen ? 'w-80' : 'w-0'} flex shrink-0 flex-col overflow-hidden border-r border-slate-200 bg-gradient-to-b from-white via-slate-50/80 to-blue-50/30 transition-all duration-300 shadow-sm shadow-slate-200/40`}
      aria-label="Course sidebar"
    >
      <div className="shrink-0 border-b border-slate-200 bg-gradient-to-r from-white to-blue-50/50 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-blue-700/90">
              Course Progress
            </p>
            <p className="text-xs font-medium text-slate-600">
              {completed} of {total} lessons completed
            </p>
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 md:hidden"
            aria-label="Close sidebar"
            onClick={onClose}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200/90 ring-1 ring-slate-200">
            <div
              className="h-full rounded-full transition-all shadow-sm shadow-blue-900/5"
              style={{ width: `${percent}%`, backgroundImage: PRO_BLUE_STRIP }}
            />
          </div>
          <span className="shrink-0 text-xs font-semibold tabular-nums tracking-wide text-blue-700">
            {percent}%
          </span>
        </div>
      </div>

      {!error && (
        <div className="flex-1 overflow-y-auto">
          {sections.map((section) => {
            const expanded = playbackNavLocked ? true : Boolean(openSections[section.id])
            const module = modules.find((m) => m.id === section.id)
            const showModuleQuiz = !playbackNavLocked && hasAvailableModuleQuiz(module)
            return (
              <div key={section.id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-lg border border-slate-200/90 bg-white/80 px-4 py-2.5 text-left text-xs font-semibold tracking-wide text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/40"
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
                    {showModuleQuiz && module ? (
                      <ModuleQuizItem
                        courseId={courseId}
                        module={module}
                        sectionLessons={section.lessons}
                        activeLessonId={activeLessonId}
                      />
                    ) : null}
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

  const nextQuizHref = useMemo(() => {
    if (playbackNavLocked) return null
    const sections = groupLessonsByModule(lessons, modules)
    const activeSection = sections.find((section) =>
      section.lessons.some((lesson) => lesson.id === lessonId),
    )
    if (!activeSection) return null

    const lastLessonInSection = activeSection.lessons[activeSection.lessons.length - 1]
    if (lastLessonInSection?.id !== lessonId) return null

    const activeModule = modules.find((module) => module.id === activeSection.id)
    return hasAvailableModuleQuiz(activeModule)
      ? moduleQuizLinkTo(courseId, activeModule.id, lessonPlayerPath(courseId, lessonId))
      : null
  }, [courseId, lessonId, lessons, modules, playbackNavLocked])

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

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const nextHeaderHref = nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gradient-to-br from-slate-100 via-white to-blue-50/70">
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

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex shrink-0 flex-col">
          <div
            className="h-1 w-full shrink-0 bg-gradient-to-r from-blue-400 via-blue-600 to-sky-500"
            aria-hidden
          />
          <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-gradient-to-r from-white via-white to-blue-50/60 px-4 py-3 shadow-sm shadow-slate-200/40">
          <button
            type="button"
            onClick={() => setSidebarOpen((s) => !s)}
            className="rounded-lg p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
            aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>

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
            {prevLesson ? (
              playbackNavLocked ? (
                <span className="inline-flex cursor-not-allowed items-center rounded-lg border border-slate-200 bg-slate-100 px-3 py-1.5 text-sm text-slate-400 opacity-90">
                  <svg className="mr-1.5 h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Prev
                </span>
              ) : (
                <Link
                  to={`/courses/${courseId}/lessons/${prevLesson.id}`}
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

        <div className="flex-1 overflow-y-auto bg-gradient-to-b from-transparent via-white/50 to-blue-50/30">
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
