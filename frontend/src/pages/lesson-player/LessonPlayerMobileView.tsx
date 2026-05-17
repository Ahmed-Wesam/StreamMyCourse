import { useEffect, useState, type RefObject, type SyntheticEvent } from 'react'
import { Link, type To } from 'react-router-dom'
import type { CourseModule, CourseProgress, Lesson } from '../../lib/api'
import {
  CourseLessonsCurriculum,
  LessonPlayerAlerts,
  LessonUpNextCard,
  PRO_BLUE_STRIP,
  VideoSkeleton,
} from './lessonPlayerUi'

export type LessonPlayerMobileViewProps = {
  courseId: string
  lessons: Lesson[]
  modules: CourseModule[]
  lessonId: string
  activeLessonTitle: string
  activeModuleLabel: string
  loading: boolean
  src: string | null
  videoRef: RefObject<HTMLVideoElement | null>
  onLoadedMetadata: () => void
  onTimeUpdate: (e: SyntheticEvent<HTMLVideoElement>) => void
  onEnded: () => void
  onPause: () => void
  needsSignIn: boolean
  needsEnrollment: boolean
  enrolling: boolean
  error: string | null
  onEnroll: () => void
  playbackNavLocked: boolean
  courseProgress: CourseProgress | null
  isLessonCompleted: boolean
  onMarkComplete: () => void
  onMarkIncomplete: () => void
  prevLesson: Lesson | null
  prevQuizHref?: To | null
  nextLesson: Lesson | null
  nextQuizHref?: To | null
}

export function LessonPlayerMobileView({
  courseId,
  lessons,
  modules,
  lessonId,
  activeLessonTitle,
  activeModuleLabel,
  loading,
  src,
  videoRef,
  onLoadedMetadata,
  onTimeUpdate,
  onEnded,
  onPause,
  needsSignIn,
  needsEnrollment,
  enrolling,
  error,
  onEnroll,
  playbackNavLocked,
  courseProgress,
  isLessonCompleted,
  onMarkComplete,
  onMarkIncomplete,
  prevLesson,
  prevQuizHref,
  nextLesson,
  nextQuizHref,
}: LessonPlayerMobileViewProps) {
  const [curriculumOpen, setCurriculumOpen] = useState(false)

  useEffect(() => {
    setCurriculumOpen(false)
  }, [lessonId])

  useEffect(() => {
    if (!curriculumOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [curriculumOpen])

  const upNextTitle = nextQuizHref ? 'Module quiz' : nextLesson?.title
  const upNextDescription = nextQuizHref ? 'Continue to the module quiz' : 'Continue to the next lesson'
  const prevHref =
    prevQuizHref ?? (prevLesson ? `/courses/${courseId}/lessons/${prevLesson.id}` : null)
  const nextHref =
    nextQuizHref ?? (nextLesson ? `/courses/${courseId}/lessons/${nextLesson.id}` : null)
  const percent = courseProgress?.percentComplete ?? 0

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col bg-gradient-to-br from-slate-100 via-white to-blue-50/70">
      <div className="sticky top-16 z-40 shrink-0">
        <div
          className="h-1 w-full shrink-0 bg-gradient-to-r from-blue-400 via-blue-600 to-sky-500"
          aria-hidden
        />
        <header className="flex items-center justify-between gap-2 border-b border-slate-200 bg-gradient-to-r from-white via-white to-blue-50/60 px-3 py-2.5 shadow-sm shadow-slate-200/40">
        <Link
          to={`/courses/${courseId}`}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
          aria-label="Back to course"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M15 18l-6-6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Link>

        <button
          type="button"
          onClick={() => setCurriculumOpen(true)}
          className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-slate-50"
          aria-label="Open course curriculum"
        >
          <svg className="h-4 w-4 text-slate-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="hidden min-[380px]:inline">Lessons</span>
        </button>
      </header>
      </div>

      <div className="relative w-full shrink-0 bg-black">
        {loading ? (
          <VideoSkeleton edgeToEdge />
        ) : (
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
        )}
      </div>

      <div className="border-t border-slate-200 bg-gradient-to-b from-white via-white/95 to-blue-50/40">
        <div className="px-4 pb-4 pt-4">
            <LessonPlayerAlerts
              needsSignIn={needsSignIn}
              needsEnrollment={needsEnrollment}
              enrolling={enrolling}
              error={error}
              courseId={courseId}
              onEnroll={onEnroll}
              compact
            />

            {activeModuleLabel ? (
              <div className="mb-2 inline-flex max-w-full items-center rounded-full bg-gradient-to-r from-blue-50 to-slate-50 px-3 py-1 text-xs font-semibold text-blue-800 ring-1 ring-blue-100/80">
                <span className="truncate">{activeModuleLabel}</span>
              </div>
            ) : null}
            <h1 className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-800 bg-clip-text text-xl font-bold tracking-tight text-transparent">
              {activeLessonTitle}
            </h1>

            {courseProgress != null ? (
              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                  <span>Course progress</span>
                  <span className="font-semibold tabular-nums text-blue-700">{percent}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-200/90 ring-1 ring-slate-200">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${percent}%`, backgroundImage: PRO_BLUE_STRIP }}
                  />
                </div>
              </div>
            ) : null}

            <button
              type="button"
              disabled={loading || playbackNavLocked}
              onClick={isLessonCompleted ? onMarkIncomplete : onMarkComplete}
              className={`mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
                isLessonCompleted
                  ? 'border border-slate-200 bg-white text-slate-700 shadow-sm'
                  : 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md shadow-blue-900/15'
              }`}
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M20 6 9 17l-5-5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {isLessonCompleted ? 'Mark as Incomplete' : 'Mark as Complete'}
            </button>

            {upNextTitle ? (
              <LessonUpNextCard
                upNextTitle={upNextTitle}
                upNextDescription={upNextDescription}
                playbackNavLocked={playbackNavLocked}
              />
            ) : null}
        </div>

        <nav
          className="shrink-0 border-t border-slate-200 bg-white px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
          aria-label="Lesson navigation"
        >
          <div className="flex items-center gap-3">
            {prevHref ? (
              playbackNavLocked ? (
                <span className="inline-flex min-h-11 flex-1 cursor-not-allowed items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-sm font-medium text-slate-400">
                  Previous
                </span>
              ) : (
                <Link
                  to={prevHref}
                  className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 shadow-sm active:bg-slate-50"
                >
                  Previous
                </Link>
              )
            ) : (
              <div className="flex-1" />
            )}

            {nextHref ? (
              playbackNavLocked ? (
                <span className="inline-flex min-h-11 flex-1 cursor-not-allowed items-center justify-center rounded-xl bg-slate-100 text-sm font-semibold text-slate-400">
                  Next
                </span>
              ) : (
                <Link
                  to={nextHref}
                  className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 text-sm font-semibold text-white shadow-md active:from-blue-700 active:to-blue-800"
                >
                  Next
                </Link>
              )
            ) : playbackNavLocked ? (
              <Link
                to={`/courses/${courseId}`}
                className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 shadow-sm active:bg-slate-50"
              >
                Course page
              </Link>
            ) : (
              <div className="flex-1" />
            )}
          </div>
        </nav>
      </div>

      {curriculumOpen ? (
        <div className="fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true" aria-label="Course lessons">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-[2px]"
            aria-label="Close curriculum"
            onClick={() => setCurriculumOpen(false)}
          />
          <div className="relative flex max-h-[min(88dvh,720px)] flex-col overflow-hidden rounded-t-2xl bg-white shadow-2xl">
            <div className="flex shrink-0 justify-center pt-2 pb-1" aria-hidden="true">
              <div className="h-1 w-10 rounded-full bg-slate-300" />
            </div>
            <CourseLessonsCurriculum
              error={error}
              lessons={lessons}
              modules={modules}
              courseId={courseId}
              activeLessonId={lessonId}
              playbackNavLocked={playbackNavLocked}
              courseProgress={courseProgress}
              onClose={() => setCurriculumOpen(false)}
              showCloseButton
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}
