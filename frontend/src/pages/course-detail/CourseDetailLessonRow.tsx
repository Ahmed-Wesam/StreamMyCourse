import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isHttpsUrl } from '../../lib/isHttpsUrl'
import type { Lesson } from '../../lib/api/types'

type CourseDetailLessonRowProps = {
  lesson: Lesson
  courseId: string
  index: number
  linkDisabled: boolean
  showActions: boolean
  completed: boolean
  markingComplete: boolean
  onToggleComplete: (lesson: Lesson, nextCompleted: boolean) => void
  thumbnailProgressPercent: number | null
}

export function CourseDetailLessonRow({
  lesson,
  courseId,
  index,
  linkDisabled,
  showActions,
  completed,
  markingComplete,
  onToggleComplete,
  thumbnailProgressPercent,
}: CourseDetailLessonRowProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const lessonThumb = lesson.thumbnailUrl && isHttpsUrl(lesson.thumbnailUrl) ? lesson.thumbnailUrl : null

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
    'group block pt-4 pb-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-rs-blue ' +
    (linkDisabled ? 'cursor-default opacity-80' : 'cursor-pointer hover:bg-rs-sky-2/80 transition-colors')

  const mainRow = (
    <div className="flex items-center pb-3">
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg bg-rs-sky-2 text-rs-blue">
        {lessonThumb ? (
          <img src={lessonThumb} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-sm font-semibold group-hover:bg-rs-blue group-hover:text-white transition-colors">
            {index + 1}
          </span>
        )}
      </div>
      <div className="ml-4 flex-1 min-w-0">
        <h3 className="font-semibold text-rs-ink transition-colors group-hover:text-rs-blue">{lesson.title}</h3>
      </div>
      {showActions && !linkDisabled ? (
        <div className="relative ml-2 shrink-0">
          <button
            type="button"
            aria-label={`Lesson actions: ${lesson.title}`}
            className="rounded-md p-2 text-rs-muted opacity-0 transition-opacity hover:bg-rs-sky-2 hover:text-rs-blue group-hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-rs-blue"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              setMenuOpen((o) => !o)
            }}
            onMouseDown={(e) => {
              e.stopPropagation()
            }}
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M10 6.5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 5a1.5 1.5 0 110-3 1.5 1.5 0 010 3z" />
            </svg>
          </button>
          {menuOpen ? (
            <div
              role="menu"
              aria-label={`Lesson menu: ${lesson.title}`}
              className="absolute right-0 top-10 z-20 w-48 overflow-hidden rounded-lg border border-rs-line bg-white shadow-rs"
              onMouseDown={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                role="menuitem"
                disabled={markingComplete}
                className="flex w-full items-center px-3 py-2 text-sm text-rs-ink hover:bg-rs-sky-2 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onToggleComplete(lesson, !completed)
                }}
              >
                {markingComplete ? 'Updating…' : completed ? 'Mark as incomplete' : 'Mark as complete'}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="flex shrink-0 items-center text-rs-blue opacity-0 transition-opacity group-hover:opacity-100">
        <span className="text-sm font-medium mr-2">{linkDisabled ? 'Locked' : 'Play'}</span>
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    </div>
  )

  const progressColor = `linear-gradient(90deg, #dc2626 0%, #eab308 50%, #16a34a 100%)`
  const progressBar =
    thumbnailProgressPercent !== null ? (
      <div
        className="relative z-10 h-[3px] w-full bg-rs-line-2"
        role="progressbar"
        aria-valuenow={thumbnailProgressPercent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Lesson watched about ${thumbnailProgressPercent}%`}
      >
        <div
          className="h-full"
          style={{
            width: `${thumbnailProgressPercent}%`,
            background: progressColor,
          }}
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
