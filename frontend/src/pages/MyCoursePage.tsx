import { ArrowRight, BookOpen, Play } from 'lucide-react'
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

type CourseRowData = {
  course: Course
  modules: CourseModule[]
  lessons: Lesson[]
  progress: CourseProgress | null
}

type PageState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; courses: CourseRowData[] }
  | { status: 'empty' }

function getContinueToPath(
  course: Course,
  resume: { lesson: Lesson; startTimeSec: number } | null,
): string | { pathname: string; search: string } | null {
  if (!resume) return null
  if (resume.startTimeSec > 0) {
    return {
      pathname: `/courses/${course.id}/lessons/${resume.lesson.id}`,
      search: `?t=${resume.startTimeSec}`,
    }
  }
  return `/courses/${course.id}/lessons/${resume.lesson.id}`
}

function clampPct(n: number) {
  return Math.min(100, Math.max(0, n))
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

function LoadingOverlay() {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 px-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Loading your courses"
    >
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-lg">
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 animate-spin rounded-full border-2 border-muted border-t-primary"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <div className="text-sm font-semibold text-foreground">Loading your courses</div>
            <div className="mt-1 text-sm text-muted-foreground">Just a moment…</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function CourseCard({ row }: { row: CourseRowData }) {
  const resume = useMemo(() => getResumeLesson(row.lessons, row.progress), [row.lessons, row.progress])
  const continueTo = useMemo(() => getContinueToPath(row.course, resume), [row.course, resume])
  const percentComplete = row.progress?.percentComplete ?? 0
  const completedCount = row.progress?.completedCount ?? 0
  const totalReadyLessons = row.progress?.totalReadyLessons ?? row.lessons.length
  const isResuming = Boolean(resume?.startTimeSec && resume.startTimeSec > 0)

  return (
    <article className="overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md">
      <div className="h-1 bg-primary/80" aria-hidden="true" />
      <div className="flex flex-col gap-6 px-6 py-6 lg:flex-row lg:items-center lg:gap-8 lg:px-8 lg:py-7">
        <div className="min-w-0 flex-[1.2] lg:max-w-md">
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            {row.modules.length} {row.modules.length === 1 ? 'module' : 'modules'}
          </div>
          <h2 className="truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">
            {row.course.title}
          </h2>
          {row.course.description ? (
            <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {row.course.description}
            </p>
          ) : null}
          <p className="mt-3 text-sm text-muted-foreground">
            {resume ? (
              <>
                Up next:{' '}
                <span className="font-semibold text-foreground">{resume.lesson.title}</span>
              </>
            ) : (
              'No lessons available yet.'
            )}
          </p>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span className="font-semibold text-foreground">{percentComplete}%</span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${clampPct(percentComplete)}%` }}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={clampPct(percentComplete)}
              aria-label={`${row.course.title} completion`}
            />
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>
              {completedCount} of {totalReadyLessons} lessons completed
            </span>
            <span>{row.lessons.length} lessons</span>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-3 lg:justify-end">
          {continueTo ? (
            <Link
              to={continueTo}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {isResuming ? 'Resume' : 'Continue'}
            </Link>
          ) : null}
          <Link
            to={`/courses/${row.course.id}`}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-muted/50"
          >
            Course details
            <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </article>
  )
}

async function loadCourseRow(course: Course): Promise<CourseRowData> {
  const [modules, lessons] = await Promise.all([listCourseModules(course.id), listLessons(course.id)])

  let progress: CourseProgress | null = null
  try {
    progress = await getCourseProgress(course.id)
  } catch {
    progress = null
  }

  return {
    course,
    modules: [...modules].sort((a, b) => a.order - b.order),
    lessons: [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order),
    progress,
  }
}

export default function MyCoursePage() {
  const [state, setState] = useState<PageState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    async function run() {
      try {
        const courses = await listCourses()
        if (courses.length === 0) {
          if (!cancelled) setState({ status: 'empty' })
          return
        }

        const rows = await Promise.all(courses.map((course) => loadCourseRow(course)))
        if (!cancelled) setState({ status: 'ready', courses: rows })
      } catch (e) {
        if (!cancelled) setState({ status: 'error', message: catalogApiUserMessage(e, 'loadCourses') })
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-10 sm:space-y-10 sm:py-12">
        {state.status === 'loading' ? <LoadingOverlay /> : null}

        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Courses</h1>
          <p className="max-w-2xl text-muted-foreground">
            Pick up where you left off across your enrolled courses.
          </p>
        </header>

        {state.status === 'error' ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6">
            <div className="text-sm font-semibold text-foreground">Couldn’t load your courses</div>
            <div className="mt-1 text-sm text-muted-foreground">{state.message}</div>
            <div className="mt-4">
              <Link
                to="/details"
                className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
              >
                View details
              </Link>
            </div>
          </div>
        ) : null}

        {state.status === 'empty' ? (
          <div className="rounded-xl border border-border bg-card p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <BookOpen className="h-6 w-6 text-primary" aria-hidden="true" />
            </div>
            <div className="text-sm font-semibold text-foreground">No courses yet</div>
            <p className="mt-1 text-sm text-muted-foreground">
              View the details page to enroll and start learning.
            </p>
            <div className="mt-6">
              <Link
                to="/details"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
              >
                View details
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        ) : null}

        {state.status === 'ready' ? (
          <div className="space-y-4">
            {state.courses.map((row) => (
              <CourseCard key={row.course.id} row={row} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
