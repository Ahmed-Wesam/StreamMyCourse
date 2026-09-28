import { Card } from '../../components/ui/Card'
import type { StudentDashboardStats } from '../../lib/studentDashboard'

type StudentDashboardStatsRowProps = {
  stats: StudentDashboardStats
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="rounded-rs-lg border border-rs-line px-5 py-4 shadow-rs-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold text-rs-ink">{value}</p>
    </Card>
  )
}

export function StudentDashboardStatsRow({ stats }: StudentDashboardStatsRowProps) {
  const active =
    stats.availability === 'ready' ? String(stats.activeCourses) : stats.availability === 'empty' ? '0' : '—'

  const overall =
    stats.availability === 'ready'
      ? `${Math.round(stats.overallProgressPercent)}%`
      : stats.availability === 'empty'
        ? '0%'
        : '—'

  const quizzes =
    stats.availability === 'ready'
      ? `${stats.quizzesPassed.passed} of ${stats.quizzesPassed.visible}`
      : stats.availability === 'empty'
        ? '0 of 0'
        : '—'

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-3"
      data-testid="student-dashboard-stats"
    >
      <StatCard label="Active courses" value={active} />
      <StatCard label="Overall progress" value={overall} />
      <StatCard label="Quizzes passed" value={quizzes} />
    </div>
  )
}
