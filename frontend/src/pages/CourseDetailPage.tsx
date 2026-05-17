import { BookOpen, ChevronLeft, Clock, Play } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  enrollInCourse,
  getCourse,
  getCourseProgress,
  hasSignedInIdToken,
  listLessons,
  listCourseModules,
  updateLessonProgress,
  type Course,
  type CourseModule,
  type CourseProgress,
  type Lesson,
  type LessonProgressItem,
} from '../lib/api'
import { catalogApiUserMessage, courseNotFoundMessage } from '../lib/apiUserMessages'
import { groupLessonsByModule } from '../lib/lessonGrouping'
import { lessonPlayerPath, moduleQuizLinkTo } from '../lib/moduleQuizNavigation'
import { PricingSection } from '../components/course/PricingSection'
import { FIGMA_MOCK_COURSE_INSTRUCTOR_NAME, FIGMA_MOCK_COURSE_PRICING_PLANS } from '../lib/figma-mocks'

/** 0–100 for the thumbnail bar, or null when no in-progress / completed state to show. */
function lessonThumbnailProgressPercent(
  lesson: Lesson,
  progressItem: LessonProgressItem | undefined,
): number | null {
  if (!progressItem) return null
  if (progressItem.completed) return 100
  const pos = progressItem.lastPositionSec
  if (pos <= 0) return null
  const duration = lesson.duration
  if (duration != null && duration > 0) {
    return Math.min(100, Math.round((pos / duration) * 100))
  }
  // Started but no duration on the lesson DTO — show a small sliver like “partially watched”.
  return 12
}

function SkeletonLesson() {
  return (
    <div className="flex items-center py-4 animate-pulse">
      <div className="h-10 w-10 rounded-lg bg-muted" />
      <div className="ml-4 flex-1">
        <div className="mb-2 h-4 w-1/3 rounded bg-muted" />
        <div className="h-3 w-1/4 rounded bg-muted" />
      </div>
    </div>
  )
}

function CourseDetailStatsStrip({
  loading,
  course,
  error,
  lessons,
  modules,
  courseProgress,
}: {
  loading: boolean
  course: Course | null
  error: string | null
  lessons: Lesson[]
  modules: CourseModule[]
  courseProgress: CourseProgress | null
}) {
  if (loading || error || !course) return null

  const stats = [
    { value: String(lessons.length), label: lessons.length === 1 ? 'Lesson' : 'Lessons' },
    { value: String(modules.length), label: modules.length === 1 ? 'Module' : 'Modules' },
    {
      value:
        courseProgress != null
          ? `${Math.round(courseProgress.percentComplete)}%`
          : '—',
      label: 'Complete',
    },
    {
      value:
        courseProgress != null
          ? `${courseProgress.completedCount}/${courseProgress.totalReadyLessons}`
          : '—',
      label: 'Lessons done',
    },
  ]

  return (
    <section aria-label="Course stats" className="border-b border-border bg-white">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-6 py-8 text-center md:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label}>
            <p className="text-primary" style={{ fontWeight: 700, fontSize: '1.6rem' }}>
              {stat.value}
            </p>
            <p className="text-sm text-muted-foreground">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function courseDetailHeroTitle(loading: boolean, course: Course | null, error: string | null): string {
  if (loading) return 'Loading…'
  if (course?.title) return course.title
  if (error === courseNotFoundMessage) return 'Course not found'
  if (error) return 'Unable to load course'
  return ''
}

function CourseDetailHero({
  loading,
  course,
  lessons,
  moduleCount,
  error,
}: {
  loading: boolean
  course: Course | null
  lessons: Lesson[]
  moduleCount: number
  error: string | null
}) {
  const heroTitle = courseDetailHeroTitle(loading, course, error)
  return (
    <section aria-label="Course hero" className="bg-primary text-primary-foreground">
      <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16 lg:py-20">
        <Link
          to="/courses"
          className="mb-8 inline-flex items-center gap-1 text-sm text-white/80 transition-colors hover:text-white"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Back to all courses
        </Link>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-x-14">
          <div>
            <h1
              className="max-w-2xl"
              style={{
                fontSize: 'clamp(1.75rem, 4vw, 2.75rem)',
                fontWeight: 700,
                lineHeight: 1.2,
              }}
            >
              {heroTitle}
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-relaxed opacity-90">
              {loading ? '' : course?.description ?? ''}
            </p>
            {!loading && course && (
              <div className="mt-6 flex flex-wrap gap-3 text-sm">
                <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2">
                  <BookOpen className="h-4 w-4" aria-hidden="true" />
                  {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'}
                </span>
                {moduleCount > 0 && (
                  <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2">
                    {moduleCount} {moduleCount === 1 ? 'module' : 'modules'}
                  </span>
                )}
                <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2">
                  <Clock className="h-4 w-4" aria-hidden="true" />
                  Self-paced
                </span>
              </div>
            )}
          </div>
          <div className="flex justify-center lg:justify-end">
            <div className="aspect-video w-full max-w-lg overflow-hidden rounded-xl border border-white/20 shadow-2xl shadow-black/20">
              {!loading && course?.thumbnailUrl ? (
                <img src={course.thumbnailUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center bg-white/10 text-sm text-white/70">
                  Course preview
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function ResumeLearningButton({
  courseId,
  lessons,
  courseProgress,
  disabled,
}: {
  courseId: string
  lessons: Lesson[]
  courseProgress: CourseProgress | null
  disabled: boolean
}) {
  const resumeInfo = getResumeLesson(lessons, courseProgress)
  const label =
    lessons.length === 0
      ? 'No lessons'
      : resumeInfo && resumeInfo.startTimeSec > 0
        ? 'Resume Learning'
        : 'Start Learning'

  if (disabled || !resumeInfo) {
    return (
      <span className="inline-flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground opacity-50">
        <Play className="h-5 w-5" aria-hidden="true" />
        {label}
      </span>
    )
  }

  const { lesson, startTimeSec } = resumeInfo
  const toPath =
    startTimeSec > 0
      ? { pathname: `/courses/${courseId}/lessons/${lesson.id}`, search: `?t=${startTimeSec}` }
      : `/courses/${courseId}/lessons/${lesson.id}`

  return (
    <Link
      to={toPath}
      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition hover:opacity-90"
    >
      <Play className="h-5 w-5" aria-hidden="true" />
      {label}
    </Link>
  )
}

/** Find the best lesson to resume from, or null if none available.
 * Returns first incomplete lesson with progress, or first lesson if all completed.
 */
function getResumeLesson(
  lessons: Lesson[],
  courseProgress: CourseProgress | null,
): { lesson: Lesson; startTimeSec: number } | null {
  if (lessons.length === 0) return null

  // Sort by module sequence, then lesson order within module.
  const sortedLessons = [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)

  // Find first incomplete lesson
  for (const lesson of sortedLessons) {
    const progress = courseProgress?.lessons.find((p) => p.lessonId === lesson.id)
    if (!progress || !progress.completed) {
      // Resume from saved position if available, otherwise from start
      const startTimeSec = progress?.lastPositionSec ?? 0
      return { lesson, startTimeSec }
    }
  }

  // All lessons completed - go to first lesson
  return { lesson: sortedLessons[0], startTimeSec: 0 }
}

function CourseDetailBody({
  courseId,
  error,
  loading,
  lessons,
  modules,
  course,
  courseProgress,
  previewOnly,
  needsEnrollment,
  enrolling,
  onEnroll,
  onToggleLessonComplete,
  markingLessonId,
}: {
  courseId: string
  error: string | null
  loading: boolean
  lessons: Lesson[]
  modules: CourseModule[]
  course: Course | null
  courseProgress: CourseProgress | null
  previewOnly: boolean
  needsEnrollment: boolean
  enrolling: boolean
  onEnroll: () => void
  onToggleLessonComplete: (lesson: Lesson, nextCompleted: boolean) => void
  markingLessonId: string | null
}) {
  const lessonSections = useMemo(() => groupLessonsByModule(lessons, modules), [lessons, modules])
  const lessonIndexById = useMemo(() => new Map(lessons.map((l, i) => [l.id, i])), [lessons])
  const moduleById = useMemo(() => new Map(modules.map((m) => [m.id, m])), [modules])
  const showModuleQuizBadge = !previewOnly && !needsEnrollment

  return (
    <section className="border-b border-border bg-secondary/40 py-12 sm:py-16">
      <div className="mx-auto max-w-6xl px-6">
      {error && (
        <div className="mb-8 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
          <div className="flex">
            <svg className="mt-0.5 h-5 w-5 text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-foreground">Error loading course</h3>
              <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="border-t border-border pt-6">
          <div className="mb-6 h-8 w-40 animate-pulse rounded bg-muted" />
          <SkeletonLesson />
          <SkeletonLesson />
          <SkeletonLesson />
        </div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-3 lg:gap-12">
          <div className="lg:col-span-2">
            <section aria-label="Curriculum">
              <h2 className="text-2xl font-bold text-foreground">Curriculum</h2>
              <p className="mt-2 text-muted-foreground">
                {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'} across {modules.length}{' '}
                {modules.length === 1 ? 'module' : 'modules'}
              </p>
              <div className="mt-8 divide-y divide-border border-t border-border">
                {lessonSections.map((section) => {
                  const moduleQuiz = moduleById.get(section.id)?.moduleQuiz
                  const quizAvailable = showModuleQuizBadge && moduleQuiz?.available === true
                  const quizReturnLesson = section.lessons[section.lessons.length - 1]
                  const quizTo =
                    quizAvailable && quizReturnLesson
                      ? moduleQuizLinkTo(
                          courseId,
                          section.id,
                          lessonPlayerPath(courseId, quizReturnLesson.id),
                        )
                      : quizAvailable
                        ? `/courses/${courseId}/modules/${section.id}/quiz`
                        : null
                  return (
                  <div key={section.id}>
                    <div className="px-1 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-semibold text-foreground">{section.title}</div>
                        {quizAvailable && (
                          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/20">
                            Module quiz
                          </span>
                        )}
                        {quizTo ? (
                          <Link
                            to={quizTo}
                            className="ml-auto inline-flex items-center rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition hover:opacity-90"
                          >
                            Start quiz
                          </Link>
                        ) : null}
                      </div>
                      {section.description && (
                        <div className="mt-1 text-sm text-muted-foreground">{section.description}</div>
                      )}
                    </div>
                    {section.lessons.map((lesson) => (
                      <LessonItem
                        key={lesson.id}
                        lesson={lesson}
                        courseId={courseId}
                        index={lessonIndexById.get(lesson.id) ?? 0}
                        linkDisabled={previewOnly || needsEnrollment}
                        showActions={!previewOnly && !needsEnrollment}
                        completed={courseProgress?.lessons.find((p) => p.lessonId === lesson.id)?.completed ?? false}
                        markingComplete={markingLessonId === lesson.id}
                        onToggleComplete={onToggleLessonComplete}
                        thumbnailProgressPercent={lessonThumbnailProgressPercent(
                          lesson,
                          courseProgress?.lessons.find((p) => p.lessonId === lesson.id),
                        )}
                      />
                    ))}
                  </div>
                  )
                })}
              </div>
              {lessonSections.length === 0 && (
                <div className="py-12 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <h3 className="font-medium text-foreground">No lessons yet</h3>
                  <p className="mt-1 text-sm text-muted-foreground">This course doesn't have any lessons.</p>
                </div>
              )}
            </section>
          </div>

          <aside className="lg:col-span-1 lg:border-l lg:border-border lg:pl-10">
            <div className="lg:sticky lg:top-28 space-y-6">
              <h3 className="text-lg font-semibold text-foreground">About this course</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {course?.description || 'No description available.'}
              </p>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Instructor</div>
                {/* TODO(figma-backend) GAP-S2-002: replace FIGMA_MOCK_COURSE_INSTRUCTOR_NAME with a real instructor display name on the course DTO. */}
                <div className="mt-1 text-sm font-semibold text-foreground">{FIGMA_MOCK_COURSE_INSTRUCTOR_NAME}</div>
              </div>
              <div className="space-y-3 border-t border-border pt-6">
                {needsEnrollment && (
                  <button
                    type="button"
                    onClick={() => void onEnroll()}
                    disabled={enrolling}
                    className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {enrolling ? 'Enrolling…' : 'Enroll for free'}
                  </button>
                )}
                {previewOnly && (
                  <p className="text-center text-sm text-muted-foreground">
                    <Link to="/login" className="font-medium text-primary hover:opacity-90">
                      Sign in
                    </Link>{' '}
                    to enroll and watch lessons.
                  </p>
                )}
                <ResumeLearningButton
                  courseId={courseId}
                  lessons={lessons}
                  courseProgress={courseProgress}
                  disabled={lessons.length === 0 || previewOnly || needsEnrollment}
                />
              </div>
            </div>
          </aside>
        </div>
      )}
      </div>
    </section>
  )
}

function LessonItem({
  lesson,
  courseId,
  index,
  linkDisabled,
  showActions,
  completed,
  markingComplete,
  onToggleComplete,
  thumbnailProgressPercent,
}: {
  lesson: Lesson
  courseId: string
  index: number
  linkDisabled: boolean
  showActions: boolean
  completed: boolean
  markingComplete: boolean
  onToggleComplete: (lesson: Lesson, nextCompleted: boolean) => void
  thumbnailProgressPercent: number | null
}) {
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    const onMouseDown = () => setMenuOpen(false)
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onMouseDown)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onMouseDown)
    }
  }, [menuOpen])

  const rowShell =
    'group block pt-4 pb-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary ' +
    (linkDisabled ? 'cursor-default opacity-80' : 'cursor-pointer hover:bg-primary/5 transition-colors')

  const mainRow = (
    <div className="flex items-center pb-3">
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg bg-primary/10 text-primary">
        {lesson.thumbnailUrl ? (
          <img src={lesson.thumbnailUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-sm font-semibold group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
            {index + 1}
          </span>
        )}
      </div>
      <div className="ml-4 flex-1 min-w-0">
        <h3 className="font-medium text-foreground transition-colors group-hover:text-primary">
          {lesson.title}
        </h3>
      </div>
      {showActions && !linkDisabled && (
        <div className="relative ml-2 shrink-0">
          <button
            type="button"
            aria-label={`Lesson actions: ${lesson.title}`}
            className="rounded-md p-2 text-muted-foreground opacity-0 transition-opacity hover:bg-primary/10 hover:text-primary group-hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              setMenuOpen((o) => !o)
            }}
            onMouseDown={(e) => {
              // Prevent the global mousedown listener from closing immediately.
              e.stopPropagation()
            }}
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M10 6.5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 5a1.5 1.5 0 110-3 1.5 1.5 0 010 3z" />
            </svg>
          </button>
          {menuOpen && (
            <div
              role="menu"
              aria-label={`Lesson menu: ${lesson.title}`}
              className="absolute right-0 top-10 z-20 w-48 overflow-hidden rounded-lg border border-border bg-card shadow-lg"
              onMouseDown={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                role="menuitem"
                disabled={markingComplete}
                className="flex w-full items-center px-3 py-2 text-sm text-foreground hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onToggleComplete(lesson, !completed)
                }}
              >
                {markingComplete ? 'Updating…' : completed ? 'Mark as incomplete' : 'Mark as complete'}
              </button>
            </div>
          )}
        </div>
      )}
      <div className="flex shrink-0 items-center text-primary opacity-0 transition-opacity group-hover:opacity-100">
        <span className="text-sm font-medium mr-2">{linkDisabled ? 'Locked' : 'Play'}</span>
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    </div>
  )

  // Calculate gradient color from red (0%) to green (100%) based on completion
  const progressColor =
    thumbnailProgressPercent !== null
      ? `linear-gradient(90deg, #dc2626 0%, #eab308 50%, #16a34a 100%)`
      : undefined
  const progressStyle =
    thumbnailProgressPercent !== null
      ? {
          width: `${thumbnailProgressPercent}%`,
          background: progressColor,
        }
      : undefined

  const progressBar =
    thumbnailProgressPercent !== null ? (
      <div
        className="relative z-10 h-[3px] w-full bg-muted"
        role="progressbar"
        aria-valuenow={thumbnailProgressPercent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Lesson watched about ${thumbnailProgressPercent}%`}
      >
        <div
          className="h-full"
          style={progressStyle}
        />
      </div>
    ) : null

  if (linkDisabled) {
    return (
      <div className={rowShell}>
        {mainRow}
        {progressBar}
      </div>
    )
  }
  return (
    <Link to={`/courses/${courseId}/lessons/${lesson.id}`} className={rowShell}>
      {mainRow}
      {progressBar}
    </Link>
  )
}

export default function CourseDetailPage() {
  const params = useParams()
  const courseId = useMemo(() => params.courseId ?? '', [params.courseId])

  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [modules, setModules] = useState<CourseModule[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [previewOnly, setPreviewOnly] = useState(false)
  const [needsEnrollment, setNeedsEnrollment] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [courseProgress, setCourseProgress] = useState<CourseProgress | null>(null)
  const [markingLessonId, setMarkingLessonId] = useState<string | null>(null)

  const loadCourseData = useCallback(async () => {
    setError(null)
    setLoading(true)
    setCourseProgress(null)
    const signedIn = await hasSignedInIdToken()
    setPreviewOnly(!signedIn)
    setNeedsEnrollment(false)
    try {
      const [c, l, m] = await Promise.all([getCourse(courseId), listLessons(courseId), listCourseModules(courseId)])
      if (!c) {
        setCourse(null)
        setLessons([])
        setModules([])
        setError(courseNotFoundMessage)
        return
      }
      setCourse(c)
      setModules([...m].sort((a, b) => a.order - b.order))
      setLessons([...l].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order))
      if (signedIn) {
        setNeedsEnrollment(c.enrolled === false)
      }
      if (signedIn) {
        try {
          const prog = await getCourseProgress(courseId)
          setCourseProgress(prog)
        } catch {
          // Silently ignore expected progress errors (RDS unavailable, auth not configured, enrollment required)
          setCourseProgress(null)
        }
      }
    } catch (e) {
      setError(catalogApiUserMessage(e, 'loadCourse'))
      setCourse(null)
      setLessons([])
      setModules([])
    } finally {
      setLoading(false)
    }
  }, [courseId])

  const onToggleLessonComplete = useCallback(
    (lesson: Lesson, nextCompleted: boolean) => {
      if (!courseId) return
      void (async () => {
        if (markingLessonId) return
        setMarkingLessonId(lesson.id)
        try {
          const res = await updateLessonProgress(courseId, lesson.id, {
            lastPositionSec: 0,
            durationSec: lesson.duration ?? 0,
            ...(nextCompleted ? { markComplete: true } : { markIncomplete: true }),
          })
          const updated = res.lessonProgress
          if (!updated) return
          setCourseProgress((prev) => {
            if (!prev) return prev
            const lessons = prev.lessons.map((p) =>
              p.lessonId === updated.lessonId
                ? { ...p, completed: updated.completed, lastPositionSec: updated.lastPositionSec, completedAt: updated.completedAt }
                : p,
            )
            const completedCount = lessons.filter((l) => l.completed).length
            const percentComplete =
              prev.totalReadyLessons > 0 ? Math.round((completedCount / prev.totalReadyLessons) * 10000) / 100 : 0
            return { ...prev, lessons, completedCount, percentComplete }
          })
        } catch {
          return
        } finally {
          setMarkingLessonId(null)
        }
      })()
    },
    [courseId, markingLessonId],
  )

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
      setError(catalogApiUserMessage(e, 'enroll'))
    } finally {
      setEnrolling(false)
    }
  }, [courseId, loadCourseData])

  return (
    <div className="min-h-screen bg-background">
      <CourseDetailHero
        loading={loading}
        course={course}
        lessons={lessons}
        moduleCount={modules.length}
        error={error}
      />
      <CourseDetailStatsStrip
        loading={loading}
        course={course}
        error={error}
        lessons={lessons}
        modules={modules}
        courseProgress={courseProgress}
      />
      <CourseDetailBody
        courseId={courseId}
        error={error}
        loading={loading}
        lessons={lessons}
        modules={modules}
        course={course}
        courseProgress={courseProgress}
        previewOnly={previewOnly}
        needsEnrollment={needsEnrollment}
        enrolling={enrolling}
        onEnroll={onEnroll}
        onToggleLessonComplete={onToggleLessonComplete}
        markingLessonId={markingLessonId}
      />
      {/* Pricing visuals per Figma Make; backend wiring pending. */}
      {/* TODO(figma-backend) GAP-S2-003: replace FIGMA_MOCK_COURSE_PRICING_PLANS with real course pricing / checkout integration. */}
      {FIGMA_MOCK_COURSE_PRICING_PLANS.length > 0 && <PricingSection variant="band" />}
    </div>
  )
}
