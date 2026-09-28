import { BookOpen } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import type { StudentDashboardCourseRow } from '../../lib/studentDashboard'

type StudentDashboardContinueSectionProps = {
  rows: StudentDashboardCourseRow[]
}

export function StudentDashboardContinueSection({ rows }: StudentDashboardContinueSectionProps) {
  if (rows.length === 0) {
    return (
      <div
        className="mx-auto flex max-w-lg flex-col items-center gap-4 rounded-rs-lg border border-dashed border-rs-line px-6 py-10 text-center"
        data-testid="student-dashboard-empty"
      >
        <BookOpen className="size-10 text-rs-blue" aria-hidden />
        <p className="text-rs-body">You do not have any courses yet. Browse the catalog to get started.</p>
        <Button to="/courses" variant="ghost">
          Browse courses
        </Button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2" data-testid="student-dashboard-continue">
      {rows.map((row) => (
        <Card
          key={row.courseId}
          className="flex h-full flex-col rounded-rs-lg border border-rs-line px-6 py-5 shadow-rs-sm"
          data-testid={`student-dashboard-course-${row.courseId}`}
        >
          <h3 className="text-lg font-extrabold text-rs-ink">{row.title}</h3>
          <p className="mt-2 text-sm text-rs-body">
            {row.percentComplete === 'unavailable'
              ? 'Progress unavailable'
              : `${Math.round(row.percentComplete)}% complete`}
          </p>
          {row.subline ? (
            <p className="mt-1 text-xs text-rs-muted">
              Module {row.subline.moduleIndex} of {row.subline.moduleCount} · {row.subline.lessonTitle}
            </p>
          ) : null}
          <div className="mt-4">
            <Button to={row.continueHref} className="w-full sm:w-auto">
              Continue
            </Button>
          </div>
        </Card>
      ))}
    </div>
  )
}
