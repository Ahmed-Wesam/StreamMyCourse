import { useEffect, useMemo, useState } from 'react'
import { Link, type To } from 'react-router-dom'
import type { CourseModule, CourseProgress, Lesson } from '../../lib/api'
import { formatModuleQuizQuestionCount, quizScorePercentPillClass } from '../../lib/quizScoreDisplay'
import { groupLessonsByModule } from '../../lib/lessonGrouping'
import { lessonPlayerPath, moduleQuizLinkTo } from '../../lib/moduleQuizNavigation'

/** Progress fills — layered blues (professional). */
export const PRO_BLUE_STRIP =
  'linear-gradient(90deg, #bfdbfe, #93c5fd, #60a5fa, #3b82f6, #2563eb, #60a5fa)'
/** Compact chrome (e.g. Up next icon shell) — white through sky into blue. */
export const PRO_BLUE_FRAME =
  'linear-gradient(155deg, #ffffff, #eff6ff, #dbeafe, #93c5fd, #60a5fa)'

export function formatDurationMmSs(durationSec: number | undefined): string {
  if (!durationSec || durationSec <= 0) return ''
  const total = Math.round(durationSec)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function sortModulesByOrder(modules: CourseModule[]) {
  return [...modules].sort((a, b) => a.order - b.order)
}

export function sortLessonsByOrdering(lessons: Lesson[]) {
  return [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)
}

export function hasAvailableModuleQuiz(
  module: CourseModule | undefined,
): module is CourseModule & { moduleQuiz: { available: true; servedCountN: number } } {
  return module?.moduleQuiz?.available === true
}

/** Next target when finishing the last lesson in a module (current module quiz, then quiz-only modules). */
export function resolveNextModuleQuizHref({
  courseId,
  lessonId,
  lessons,
  modules,
  playbackNavLocked,
}: {
  courseId: string
  lessonId: string
  lessons: Lesson[]
  modules: CourseModule[]
  playbackNavLocked: boolean
}): To | null {
  if (playbackNavLocked) return null

  const sortedModules = sortModulesByOrder(modules)
  const sortedLessons = sortLessonsByOrdering(lessons)
  const activeLesson = sortedLessons.find((lesson) => lesson.id === lessonId)
  if (!activeLesson) return null

  const moduleLessons = sortedLessons.filter((lesson) => lesson.moduleId === activeLesson.moduleId)
  const lastLessonInModule = moduleLessons[moduleLessons.length - 1]
  if (lastLessonInModule?.id !== lessonId) return null

  const moduleIndex = sortedModules.findIndex((module) => module.id === activeLesson.moduleId)
  if (moduleIndex < 0) return null

  const returnTo = lessonPlayerPath(courseId, lessonId)
  const currentModule = sortedModules[moduleIndex]
  if (hasAvailableModuleQuiz(currentModule)) {
    return moduleQuizLinkTo(courseId, currentModule.id, returnTo)
  }

  for (let i = moduleIndex + 1; i < sortedModules.length; i++) {
    const mod = sortedModules[i]!
    const modLessonCount = sortedLessons.filter((lesson) => lesson.moduleId === mod.id).length
    if (modLessonCount > 0) break
    if (hasAvailableModuleQuiz(mod)) {
      return moduleQuizLinkTo(courseId, mod.id, returnTo)
    }
  }

  return null
}

/** Previous target when starting a module (prior module quiz, including quiz-only modules). */
export function resolvePrevModuleQuizHref({
  courseId,
  lessonId,
  lessons,
  modules,
  playbackNavLocked,
}: {
  courseId: string
  lessonId: string
  lessons: Lesson[]
  modules: CourseModule[]
  playbackNavLocked: boolean
}): To | null {
  if (playbackNavLocked) return null

  const sortedModules = sortModulesByOrder(modules)
  const sortedLessons = sortLessonsByOrdering(lessons)
  const activeLesson = sortedLessons.find((lesson) => lesson.id === lessonId)
  if (!activeLesson) return null

  const moduleLessons = sortedLessons.filter((lesson) => lesson.moduleId === activeLesson.moduleId)
  const firstLessonInModule = moduleLessons[0]
  if (firstLessonInModule?.id !== lessonId) return null

  const moduleIndex = sortedModules.findIndex((module) => module.id === activeLesson.moduleId)
  if (moduleIndex < 0) return null

  const returnTo = lessonPlayerPath(courseId, lessonId)

  for (let i = moduleIndex - 1; i >= 0; i--) {
    const mod = sortedModules[i]!
    const modLessonCount = sortedLessons.filter((lesson) => lesson.moduleId === mod.id).length
    if (modLessonCount === 0) {
      if (hasAvailableModuleQuiz(mod)) {
        return moduleQuizLinkTo(courseId, mod.id, returnTo)
      }
      continue
    }
    if (hasAvailableModuleQuiz(mod)) {
      return moduleQuizLinkTo(courseId, mod.id, returnTo)
    }
    return null
  }

  return null
}

export function LessonItem({
  lesson,
  courseId,
  active,
  linkDisabled,
  completed,
  progressPct,
  durationLabel,
  onNavigate,
}: {
  lesson: Lesson
  courseId: string
  active: boolean
  linkDisabled: boolean
  completed?: boolean
  progressPct?: number
  durationLabel?: string
  onNavigate?: () => void
}) {
  const rowClass = `group flex items-start px-4 py-3 transition-colors ${
    active
      ? 'border-l-[3px] border-blue-600 bg-gradient-to-r from-blue-50 to-white shadow-sm'
      : linkDisabled
        ? 'cursor-default border-l-4 border-transparent opacity-80'
        : 'border-l-4 border-transparent hover:bg-slate-50 active:bg-slate-100'
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
              <div className="h-full w-full" style={{ backgroundImage: PRO_BLUE_STRIP }} />
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
    <Link to={`/courses/${courseId}/lessons/${lesson.id}`} className={rowClass} onClick={onNavigate}>
      {inner}
    </Link>
  )
}

export function VideoSkeleton({ edgeToEdge = false }: { edgeToEdge?: boolean }) {
  return (
    <div
      className={`flex aspect-video animate-pulse items-center justify-center overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 ${
        edgeToEdge ? '' : 'rounded-xl shadow-sm'
      }`}
    >
      <div className="h-12 w-12 rounded-full bg-slate-700/60" />
    </div>
  )
}

export function ModuleQuizItem({
  courseId,
  module,
  sectionLessons,
  activeLessonId,
  onNavigate,
}: {
  courseId: string
  module: CourseModule
  sectionLessons: Lesson[]
  activeLessonId: string
  onNavigate?: () => void
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
      onClick={onNavigate}
      className="group flex items-start border-l-4 border-transparent px-4 py-3 transition-colors hover:bg-slate-50 active:bg-slate-100"
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
          <div className="flex shrink-0 items-center gap-2 pt-0.5">
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-100">
              Quiz
            </span>
            {latestScorePercent != null ? (
              <span className={`${quizScorePercentPillClass(latestScorePercent)} mt-0.5`}>
                {latestScorePercent}%
              </span>
            ) : null}
          </div>
        </div>
        <p className="mt-0.5 truncate text-xs text-slate-500">
          {servedCount ? formatModuleQuizQuestionCount(servedCount) : 'Quiz'}
        </p>
      </div>
    </Link>
  )
}

export function LessonUpNextCard({
  upNextTitle,
  upNextDescription,
  playbackNavLocked,
}: {
  upNextTitle: string
  upNextDescription: string
  playbackNavLocked: boolean
}) {
  return (
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
          <div className="text-[11px] font-semibold uppercase tracking-wider text-blue-600/90">Up next</div>
          <div className="mt-1 truncate text-sm font-semibold text-slate-900">{upNextTitle}</div>
          <div className="mt-0.5 text-xs text-slate-500">
            {playbackNavLocked ? 'Complete this lesson to unlock' : upNextDescription}
          </div>
        </div>
      </div>
    </div>
  )
}

export function LessonPlayerAlerts({
  needsSignIn,
  needsEnrollment,
  enrolling,
  error,
  courseId,
  onEnroll,
  compact = false,
}: {
  needsSignIn: boolean
  needsEnrollment: boolean
  enrolling: boolean
  error: string | null
  courseId: string
  onEnroll: () => void
  compact?: boolean
}) {
  const cardClass = compact
    ? 'mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm'
    : 'mb-6 rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-white to-blue-50/50 p-5 shadow-sm shadow-slate-200/60 ring-1 ring-blue-100/80'

  return (
    <>
      {needsSignIn && (
        <div className={cardClass}>
          <h3 className="text-sm font-semibold text-slate-900">Sign in to watch</h3>
          <p className="mt-1 text-sm text-slate-600">
            Sign in to your account to play this lesson and track your progress.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              to="/login"
              className="inline-flex min-h-11 items-center rounded-lg bg-gradient-to-r from-blue-600 via-blue-600 to-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-900/15 transition-all hover:from-blue-700 hover:to-blue-800"
            >
              Sign in
            </Link>
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/60"
            >
              Course page
            </Link>
          </div>
        </div>
      )}

      {needsEnrollment && (
        <div
          className={
            compact
              ? 'mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm'
              : 'mb-6 rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-blue-50/30 to-slate-50/80 p-5 shadow-sm shadow-slate-200/60 ring-1 ring-slate-100'
          }
        >
          <h3 className="text-sm font-semibold text-slate-900">Enroll to watch</h3>
          <p className="mt-1 text-sm text-slate-600">
            You need to enroll in this course before playback is available.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={enrolling}
              onClick={onEnroll}
              className="min-h-11 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-900/15 transition-all hover:from-blue-700 hover:to-blue-800 disabled:opacity-60"
            >
              {enrolling ? 'Enrolling…' : 'Enroll for free'}
            </button>
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/60"
            >
              Course page
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div className={`${compact ? 'mb-4' : 'mb-6'} rounded-xl border border-red-200 bg-red-50/80 p-4 shadow-sm`}>
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

export function LessonPlaybackNavigation({
  courseId,
  playbackNavLocked,
  prevLesson,
  prevQuizHref,
  nextLesson,
  nextQuizHref,
}: {
  courseId: string
  playbackNavLocked: boolean
  prevLesson: Lesson | null
  prevQuizHref?: To | null
  nextLesson: Lesson | null
  nextQuizHref?: To | null
}) {
  const prevHref = prevQuizHref ?? (prevLesson ? `/courses/${courseId}/lessons/${prevLesson.id}` : null)

  const prevLeft =
    prevHref == null ? (
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
        to={prevHref}
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

export type CourseLessonsCurriculumProps = {
  error: string | null
  lessons: Lesson[]
  modules: CourseModule[]
  courseId: string
  activeLessonId: string
  playbackNavLocked: boolean
  courseProgress: CourseProgress | null
  onClose?: () => void
  showCloseButton?: boolean
}

export function CourseLessonsCurriculum({
  error,
  lessons,
  modules,
  courseId,
  activeLessonId,
  playbackNavLocked,
  courseProgress,
  onClose,
  showCloseButton = false,
}: CourseLessonsCurriculumProps) {
  const sections = useMemo(() => groupLessonsByModule(lessons, modules), [lessons, modules])
  const percent = courseProgress?.percentComplete ?? 0
  const completed = courseProgress?.completedCount ?? 0
  const total = courseProgress?.totalReadyLessons ?? lessons.length

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})

  useEffect(() => {
    setOpenSections((prev) => {
      const next = { ...prev }
      for (const section of sections) {
        if (next[section.id] === undefined) next[section.id] = true
      }
      if (playbackNavLocked) {
        for (const section of sections) next[section.id] = true
        return next
      }
      return next
    })
  }, [sections, activeLessonId, playbackNavLocked])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
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
          {showCloseButton && onClose ? (
            <button
              type="button"
              className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              aria-label="Close curriculum"
              onClick={onClose}
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          ) : null}
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
        <div className="flex-1 overflow-y-auto overscroll-contain">
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
                          onNavigate={onClose}
                        />
                      )
                    })}
                    {showModuleQuiz && module ? (
                      <ModuleQuizItem
                        courseId={courseId}
                        module={module}
                        sectionLessons={section.lessons}
                        activeLessonId={activeLessonId}
                        onNavigate={onClose}
                      />
                    ) : null}
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function CourseLessonsSidebar({
  error,
  lessons,
  modules,
  courseId,
  activeLessonId,
  playbackNavLocked,
  courseProgress,
  sidebarOpen,
  onClose,
}: CourseLessonsCurriculumProps & {
  sidebarOpen: boolean
}) {
  return (
    <aside
      className={`${sidebarOpen ? 'w-80' : 'w-0'} hidden shrink-0 flex flex-col overflow-hidden border-r border-slate-200 bg-gradient-to-b from-white via-slate-50/80 to-blue-50/30 transition-all duration-300 shadow-sm shadow-slate-200/40 md:flex`}
      aria-label="Course sidebar"
      aria-hidden={!sidebarOpen}
    >
      {sidebarOpen ? (
        <CourseLessonsCurriculum
          error={error}
          lessons={lessons}
          modules={modules}
          courseId={courseId}
          activeLessonId={activeLessonId}
          playbackNavLocked={playbackNavLocked}
          courseProgress={courseProgress}
          onClose={onClose}
          showCloseButton={Boolean(onClose)}
        />
      ) : null}
    </aside>
  )
}
