import { Link } from 'react-router-dom'

type CourseDetailBreadcrumbProps = {
  courseTitle: string
}

export function CourseDetailBreadcrumb({ courseTitle }: CourseDetailBreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-rs-muted">
      <ol className="flex flex-wrap items-center gap-2">
        <li>
          <Link to="/" className="font-semibold text-rs-blue no-underline hover:opacity-90">
            Home
          </Link>
        </li>
        <li aria-hidden className="text-rs-line">
          /
        </li>
        <li>
          <Link to="/courses" className="font-semibold text-rs-blue no-underline hover:opacity-90">
            Courses
          </Link>
        </li>
        {courseTitle ? (
          <>
            <li aria-hidden className="text-rs-line">
              /
            </li>
            <li className="font-semibold text-rs-ink" aria-current="page">
              {courseTitle}
            </li>
          </>
        ) : null}
      </ol>
    </nav>
  )
}
