import { Link } from 'react-router-dom'

import { Card } from '../../components/ui/Card'
import type { StudentDashboardStats } from '../../lib/studentDashboard'

type StudentDashboardStatsRowProps = {
  stats: StudentDashboardStats
  /** Non-revoked certificate count; null when the certificates fetch failed. */
  certificatesCount: number | null
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="rounded-rs-lg border border-rs-line px-5 py-4 shadow-rs-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold text-rs-ink">{value}</p>
    </Card>
  )
}

function CertificatesStatCard({ value }: { value: string }) {
  return (
    <Link
      to="/certificates"
      className="block rounded-rs-lg border border-rs-line bg-white px-5 py-4 shadow-rs-sm transition-colors hover:border-rs-ink/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rs-ink"
      aria-label={`Certificates ${value}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">Certificates</p>
      <p className="mt-1 text-2xl font-extrabold text-rs-ink">{value}</p>
    </Link>
  )
}

export function StudentDashboardStatsRow({
  stats,
  certificatesCount,
}: StudentDashboardStatsRowProps) {
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

  const certificates =
    certificatesCount === null ? '—' : String(certificatesCount)

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="student-dashboard-stats"
    >
      <StatCard label="Active courses" value={active} />
      <StatCard label="Overall progress" value={overall} />
      <StatCard label="Quizzes passed" value={quizzes} />
      <CertificatesStatCard value={certificates} />
    </div>
  )
}
