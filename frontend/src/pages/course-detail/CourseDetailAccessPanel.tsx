import { Play } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import {
  courseDetailNoAccessPrompt,
  courseDetailSignInPrompt,
} from '../../lib/marketing/courseDetailShellCopy'
import type { Course, CourseProgress, Lesson } from '../../lib/api/types'
import { getResumeLesson } from './courseDetailProgress'

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
      <span className="inline-flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-full bg-rs-grad-cta px-4 py-3 text-[15px] font-bold text-white opacity-50">
        <Play className="h-5 w-5" aria-hidden />
        {label}
      </span>
    )
  }

  const { lesson, startTimeSec } = resumeInfo
  const lessonPath = `/courses/${courseId}/lessons/${lesson.id}`
  const toPath = startTimeSec > 0 ? `${lessonPath}?t=${startTimeSec}` : lessonPath

  return (
    <Button to={toPath} className="w-full" arrow>
      {label}
    </Button>
  )
}

type CourseDetailAccessPanelProps = {
  courseId: string
  course: Course | null
  lessons: Lesson[]
  courseProgress: CourseProgress | null
  previewOnly: boolean
  needsAccess: boolean
}

export function CourseDetailAccessPanel({
  courseId,
  course,
  lessons,
  courseProgress,
  previewOnly,
  needsAccess,
}: CourseDetailAccessPanelProps) {
  const canPlay = !previewOnly && !needsAccess

  return (
    <aside className="rounded-2xl border border-rs-line bg-white p-6 shadow-rs lg:sticky lg:top-28">
      <h3 className="text-lg font-extrabold text-rs-ink">About this course</h3>
      <p className="mt-2 text-sm leading-relaxed text-rs-body">
        {course?.description || 'No description available.'}
      </p>
      <div className="mt-6 space-y-4 border-t border-rs-line pt-6">
        {previewOnly ? (
          <div className="space-y-3">
            <p className="text-sm text-rs-body">{courseDetailSignInPrompt}</p>
            <Button to="/login" variant="ghost" className="w-full">
              Sign in
            </Button>
          </div>
        ) : null}
        {needsAccess ? (
          <div className="space-y-3">
            <p className="text-sm text-rs-body">{courseDetailNoAccessPrompt}</p>
            <Button to={`/checkout?productType=course&courseId=${encodeURIComponent(courseId)}`} className="w-full">
              Buy this course
            </Button>
            <Button to="/checkout?productType=bundle" variant="ghost" className="w-full">
              Buy full bundle
            </Button>
          </div>
        ) : null}
        {!previewOnly && !needsAccess && course?.hasAccess ? (
          <p className="text-sm font-semibold text-[#0d6f3e]">You own this course.</p>
        ) : null}
        {canPlay ? (
          <ResumeLearningButton
            courseId={courseId}
            lessons={lessons}
            courseProgress={courseProgress}
            disabled={lessons.length === 0}
          />
        ) : (
          <ResumeLearningButton
            courseId={courseId}
            lessons={lessons}
            courseProgress={courseProgress}
            disabled
          />
        )}
        {canPlay ? (
          <p className="text-center text-xs text-rs-muted">
            <Link to={`/courses/${courseId}#curriculum`} className="font-semibold text-rs-blue no-underline hover:opacity-90">
              View full curriculum
            </Link>
          </p>
        ) : null}
      </div>
    </aside>
  )
}
