import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getCourseProgress,
  listCourseModules,
  listCourses,
  listLessons,
  type Course,
  type CourseModule,
  type CourseProgress,
  type Lesson,
} from '../lib/api'
import { catalogApiUserMessage } from '../lib/apiUserMessages'

type FeaturedCourseState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready'
      course: Course
      modules: CourseModule[]
      lessons: Lesson[]
      progress: CourseProgress | null
    }
  | { status: 'empty' }

function getContinueToPath(
  state: FeaturedCourseState,
  featured: Course | null,
  resume: { lesson: Lesson; startTimeSec: number } | null,
): string | { pathname: string; search: string } | null {
  if (state.status !== 'ready' || !featured || !resume) return null
  if (resume.startTimeSec > 0) {
    return {
      pathname: `/courses/${featured.id}/lessons/${resume.lesson.id}`,
      search: `?t=${resume.startTimeSec}`,
    }
  }
  return `/courses/${featured.id}/lessons/${resume.lesson.id}`
}

function clampPct(n: number) {
  return Math.min(100, Math.max(0, n))
}

function LoadingOverlay() {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Loading your course"
    >
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-950/90 p-6 text-white shadow-2xl shadow-black/40 ring-1 ring-white/10">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white/80" aria-hidden="true" />
          <div className="min-w-0">
            <div className="text-sm font-semibold">Loading your course</div>
            <div className="mt-1 text-sm text-slate-300">Just a moment…</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function HeroPrimaryCta({
  status,
  continueTo,
}: {
  status: FeaturedCourseState['status']
  continueTo: string | { pathname: string; search: string } | null
}) {
  if (status === 'loading') return null
  if (!continueTo) {
    return (
      <Link
        to="/catalog"
        className="inline-flex items-center justify-center rounded-lg bg-white px-6 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100"
      >
        Browse courses
      </Link>
    )
  }
  return (
    <Link
      to={continueTo}
      className="inline-flex items-center justify-center rounded-lg bg-emerald-400/95 px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-emerald-300"
    >
      Continue learning
    </Link>
  )
}

function SummaryCardBody({
  state,
  continueTo,
  resume,
  percentComplete,
  completedCount,
  totalReadyLessons,
}: {
  state: FeaturedCourseState
  continueTo: string | { pathname: string; search: string } | null
  resume: { lesson: Lesson; startTimeSec: number } | null
  percentComplete: number
  completedCount: number
  totalReadyLessons: number
}) {
  if (state.status === 'loading') {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 w-44 rounded bg-white/10" />
        <div className="h-4 w-64 rounded bg-white/10" />
        <div className="h-2 w-full rounded bg-white/10" />
        <div className="grid grid-cols-3 gap-3">
          <div className="h-16 rounded-xl bg-white/10" />
          <div className="h-16 rounded-xl bg-white/10" />
          <div className="h-16 rounded-xl bg-white/10" />
        </div>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-4">
        <div className="text-sm font-semibold text-white">Couldn’t load your course</div>
        <div className="mt-1 text-sm text-slate-200">{state.message}</div>
        <div className="mt-4">
          <Link
            to="/catalog"
            className="inline-flex items-center justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
          >
            Go to catalog
          </Link>
        </div>
      </div>
    )
  }

  if (state.status === 'empty') {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-4">
        <div className="text-sm font-semibold text-white">No courses yet</div>
        <div className="mt-1 text-sm text-slate-200">Browse the catalog to pick a course to start learning.</div>
        <div className="mt-4">
          <Link
            to="/catalog"
            className="inline-flex items-center justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
          >
            Browse courses
          </Link>
        </div>
      </div>
    )
  }

  if (state.status !== 'ready') return null

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white/85">Featured course</div>
          <div className="mt-1 truncate text-2xl font-bold tracking-tight text-white">{state.course.title}</div>
          <div className="mt-3 text-sm leading-relaxed text-white/70">
            {resume ? (
              <>
                Up next: <span className="font-semibold text-white/85">{resume.lesson.title}</span>
              </>
            ) : (
              'This course does not have any lessons yet.'
            )}
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs text-white/70">
          <span>Progress</span>
          <span className="font-semibold text-white/85">{percentComplete}%</span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-emerald-400/95 transition-all"
            style={{ width: `${clampPct(percentComplete)}%` }}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={clampPct(percentComplete)}
            aria-label="Course completion"
          />
        </div>
        <div className="mt-2 text-xs text-white/70">
          {completedCount} of {totalReadyLessons} lessons completed
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
          <div className="text-base font-semibold text-white">{state.modules.length}</div>
          <div className="mt-0.5 text-xs text-white/70">Modules</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
          <div className="text-base font-semibold text-white">{state.lessons.length}</div>
          <div className="mt-0.5 text-xs text-white/70">Lessons</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
          <div className="text-base font-semibold text-white">{percentComplete}%</div>
          <div className="mt-0.5 text-xs text-white/70">Complete</div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {continueTo && (
          <Link
            to={continueTo}
            className="inline-flex items-center justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
          >
            {resume?.startTimeSec && resume.startTimeSec > 0 ? 'Resume' : 'Start'} lesson →
          </Link>
        )}
        <Link
          to={`/courses/${state.course.id}`}
          className="inline-flex items-center justify-center rounded-lg border border-white/20 bg-white/0 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
        >
          Course details
        </Link>
      </div>
    </div>
  )
}

function getResumeLesson(
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): { lesson: Lesson; startTimeSec: number } | null {
  if (lessons.length === 0) return null

  const sortedLessons = [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)

  for (const lesson of sortedLessons) {
    const progress = courseProgress?.lessons.find((p) => p.lessonId === lesson.id)
    if (!progress || !progress.completed) {
      const startTimeSec = progress?.lastPositionSec ?? 0
      return { lesson, startTimeSec }
    }
  }

  return { lesson: sortedLessons[0], startTimeSec: 0 }
}

export default function MyCoursePage() {
  const [state, setState] = useState<FeaturedCourseState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    async function run() {
      try {
        const courses = await listCourses()
        const featured = courses[0]
        if (!featured) {
          if (!cancelled) setState({ status: 'empty' })
          return
        }

        const [modules, lessons] = await Promise.all([
          listCourseModules(featured.id),
          listLessons(featured.id),
        ])

        let progress: CourseProgress | null = null
        try {
          progress = await getCourseProgress(featured.id)
        } catch {
          progress = null
        }

        if (!cancelled) {
          setState({
            status: 'ready',
            course: featured,
            modules: [...modules].sort((a, b) => a.order - b.order),
            lessons: [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order),
            progress,
          })
        }
      } catch (e) {
        if (!cancelled) setState({ status: 'error', message: catalogApiUserMessage(e, 'loadCourse') })
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [])

  const featured = state.status === 'ready' ? state.course : null
  const resume = useMemo(() => {
    if (state.status !== 'ready') return null
    return getResumeLesson(state.lessons, state.progress)
  }, [state])

  const continueTo = useMemo(() => getContinueToPath(state, featured, resume), [state, featured, resume])

  const percentComplete = state.status === 'ready' ? state.progress?.percentComplete ?? 0 : 0
  const completedCount = state.status === 'ready' ? state.progress?.completedCount ?? 0 : 0
  const totalReadyLessons = state.status === 'ready' ? state.progress?.totalReadyLessons ?? state.lessons.length : 0

  return (
    <div className="space-y-7 sm:space-y-10">
      {state.status === 'loading' ? <LoadingOverlay /> : null}
      <section className="overflow-hidden rounded-2xl border border-slate-600/40 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950/90 text-white shadow-xl shadow-slate-900/20 ring-1 ring-white/10 lg:rounded-3xl">
        <div className="px-6 py-12 sm:px-10 sm:py-14 lg:px-12 lg:py-16">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center lg:gap-x-14">
            <div className="min-w-0">
              <h1 className="mt-6 text-4xl font-bold leading-[1.12] tracking-tight sm:text-5xl">
                {featured ? featured.title : 'Your learning hub'}
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300 sm:text-xl">
                {featured?.description ?? 'Pick up right where you left off and keep your progress moving forward.'}
              </p>

              <div className="mt-9 flex flex-wrap gap-4">
                <HeroPrimaryCta status={state.status} continueTo={continueTo} />
              </div>
            </div>

            <div className="flex min-w-0 justify-center lg:justify-end">
              <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/25 ring-1 ring-white/10">
                <SummaryCardBody
                  state={state}
                  continueTo={continueTo}
                  resume={resume}
                  percentComplete={percentComplete}
                  completedCount={completedCount}
                  totalReadyLessons={totalReadyLessons}
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

