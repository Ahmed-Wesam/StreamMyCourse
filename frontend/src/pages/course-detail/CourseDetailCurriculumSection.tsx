import { useMemo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { groupLessonsByModule } from '../../lib/lessonGrouping'
import { lessonPlayerPath, moduleQuizLinkTo } from '../../lib/moduleQuizNavigation'
import type { CourseModule, CourseProgress, Lesson } from '../../lib/api/types'
import { CourseDetailLessonRow } from './CourseDetailLessonRow'
import { lessonThumbnailProgressPercent } from './courseDetailProgress'

function SkeletonLesson() {
  return (
    <div className="flex items-center py-4 animate-pulse">
      <div className="h-10 w-10 rounded-lg bg-rs-line-2" />
      <div className="ml-4 flex-1">
        <div className="mb-2 h-4 w-1/3 rounded bg-rs-line-2" />
        <div className="h-3 w-1/4 rounded bg-rs-line-2" />
      </div>
    </div>
  )
}

type CourseDetailCurriculumSectionProps = {
  courseId: string
  error: string | null
  loading: boolean
  lessons: Lesson[]
  modules: CourseModule[]
  courseProgress: CourseProgress | null
  previewOnly: boolean
  needsAccess: boolean
  onToggleLessonComplete: (lesson: Lesson, nextCompleted: boolean) => void
  markingLessonId: string | null
  sidebar: ReactNode
}

export function CourseDetailCurriculumSection({
  courseId,
  error,
  loading,
  lessons,
  modules,
  courseProgress,
  previewOnly,
  needsAccess,
  onToggleLessonComplete,
  markingLessonId,
  sidebar,
}: CourseDetailCurriculumSectionProps) {
  const lessonSections = useMemo(() => groupLessonsByModule(lessons, modules), [lessons, modules])
  const lessonIndexById = useMemo(() => new Map(lessons.map((l, i) => [l.id, i])), [lessons])
  const moduleById = useMemo(() => new Map(modules.map((m) => [m.id, m])), [modules])
  const showModuleQuizBadge = !previewOnly && !needsAccess
  const linkDisabled = previewOnly || needsAccess

  let body: ReactNode = null

  if (loading) {
    body = (
      <div className="border-t border-rs-line pt-6">
        <div className="mb-6 h-8 w-40 animate-pulse rounded bg-rs-line-2" />
        <SkeletonLesson />
        <SkeletonLesson />
        <SkeletonLesson />
      </div>
    )
  } else if (!error) {
    body = (
      <div className="mt-8 divide-y divide-rs-line border-t border-rs-line">
        {lessonSections.map((section) => {
          const moduleQuiz = moduleById.get(section.id)?.moduleQuiz
          const quizAvailable = showModuleQuizBadge && moduleQuiz?.available === true
          const quizReturnLesson = section.lessons[section.lessons.length - 1]
          const quizTo =
            quizAvailable && quizReturnLesson
              ? moduleQuizLinkTo(courseId, section.id, lessonPlayerPath(courseId, quizReturnLesson.id))
              : quizAvailable
                ? `/courses/${courseId}/modules/${section.id}/quiz`
                : null
          return (
            <div key={section.id}>
              <div className="px-1 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="font-bold text-rs-ink">{section.title}</div>
                  {quizAvailable ? (
                    <span className="rounded-full bg-rs-sky px-2 py-0.5 text-xs font-bold text-rs-blue ring-1 ring-[#cfdcfb]">
                      Module quiz
                    </span>
                  ) : null}
                  {quizTo ? (
                    <Link
                      to={typeof quizTo === 'string' ? quizTo : quizTo.pathname}
                      state={typeof quizTo === 'string' ? undefined : quizTo.state}
                      className="ml-auto inline-flex items-center rounded-full bg-rs-grad-cta px-3 py-1.5 text-xs font-bold text-white transition hover:opacity-90"
                    >
                      Start quiz
                    </Link>
                  ) : null}
                </div>
                {section.description ? (
                  <div className="mt-1 text-sm text-rs-body">{section.description}</div>
                ) : null}
              </div>
              {section.lessons.map((lesson) => (
                <CourseDetailLessonRow
                  key={lesson.id}
                  lesson={lesson}
                  courseId={courseId}
                  index={lessonIndexById.get(lesson.id) ?? 0}
                  linkDisabled={linkDisabled}
                  showActions={!previewOnly && !needsAccess}
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
        {lessonSections.length === 0 ? (
          <div className="py-12 text-center">
            <h3 className="font-bold text-rs-ink">No lessons yet</h3>
            <p className="mt-1 text-sm text-rs-body">This course doesn&apos;t have any lessons.</p>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <section
      id="curriculum"
      aria-label="Curriculum"
      className="scroll-mt-24 border-b border-rs-line bg-rs-sky-2/40 px-5 py-14 sm:px-7"
    >
      <div className="mx-auto max-w-wrap">
        {error ? (
          <div className="mb-8 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
            <h3 className="text-sm font-bold text-rs-ink">Error loading course</h3>
            <p className="mt-1 text-sm text-rs-body">{error}</p>
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-10 lg:grid-cols-3 lg:gap-12">
          <div className="lg:col-span-2">
            <SectionHeader
              title="Curriculum"
              lead={`${lessons.length} ${lessons.length === 1 ? 'lesson' : 'lessons'} across ${modules.length} ${modules.length === 1 ? 'module' : 'modules'}`}
              align="start"
              level={2}
            />
            {body}
          </div>
          {!loading && !error ? <div className="lg:col-span-1">{sidebar}</div> : null}
        </div>
      </div>
    </section>
  )
}
