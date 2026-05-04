import { Link } from 'react-router-dom'
import type { Course } from '../../lib/api'

type CourseCardProps = {
  course: Course
}

export function CourseCard({ course }: CourseCardProps) {
  return (
    <Link
      to={`/courses/${course.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="relative aspect-video overflow-hidden bg-slate-800">
        {course.thumbnailUrl ? (
          <img
            src={course.thumbnailUrl}
            alt=""
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-700 via-slate-800 to-slate-900">
            <svg
              className="h-14 w-14 text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        )}
        <div className="absolute bottom-3 left-3">
          <span className="rounded-full bg-black/55 px-2.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm">
            Course
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <h3 className="line-clamp-2 text-lg font-bold text-slate-900 transition-colors group-hover:text-slate-700">
          {course.title}
        </h3>
        <p className="mt-2 line-clamp-2 flex-1 text-sm text-gray-600">
          {course.description || 'Explore this course on StreamMyCourse.'}
        </p>
        <div className="mt-4 flex items-end justify-between gap-3 border-t border-gray-100 pt-4">
          <span className="text-base font-bold text-slate-900">Free</span>
          <span className="text-sm font-semibold text-slate-700 transition-colors group-hover:text-emerald-700">
            See more
            <span className="ml-1 inline-block transition-transform group-hover:translate-x-0.5">→</span>
          </span>
        </div>
      </div>
    </Link>
  )
}
