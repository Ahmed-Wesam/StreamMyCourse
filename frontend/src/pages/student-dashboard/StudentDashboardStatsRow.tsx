import { Link } from 'react-router-dom'

import type { StudentDashboardStats } from '../../lib/studentDashboard'
import { IconBook, IconMedal, IconPeople, IconTrend } from './dashboardIcons'

type StudentDashboardStatsRowProps = {
  stats: StudentDashboardStats
  /** Non-revoked certificate count; null when the certificates fetch failed. */
  certificatesCount: number | null
  /** Certified/required label from the Research Team API, or an em dash when unknown. */
  eligibility: string
}

function displayCount(stats: StudentDashboardStats): string {
  if (stats.availability === 'ready') return String(stats.activeCourses)
  if (stats.availability === 'empty') return '0'
  return '—'
}

function displayProgress(stats: StudentDashboardStats): string {
  if (stats.availability === 'ready') return `${Math.round(stats.overallProgressPercent)}%`
  if (stats.availability === 'empty') return '0%'
  return '—'
}

export function StudentDashboardStatsRow({
  stats,
  certificatesCount,
  eligibility,
}: StudentDashboardStatsRowProps) {
  const certificates = certificatesCount === null ? '—' : String(certificatesCount)

  return (
    <section className="db">
      <div className="wrap">
        <div className="stat-grid" data-testid="student-dashboard-stats">
          <div className="stat reveal" data-d="1">
            <div className="si">
              <IconBook />
            </div>
            <div className="lbl">Active Courses</div>
            <div className="val">{displayCount(stats)}</div>
            <div className="vsub">across the pathway</div>
          </div>
          <div className="stat reveal" data-d="2">
            <div className="si">
              <IconTrend />
            </div>
            <div className="lbl">Overall Progress</div>
            <div className="val">{displayProgress(stats)}</div>
            <div className="vsub">across enrolled courses</div>
          </div>
          <Link to="/certificates" className="stat reveal" data-d="3">
            <div className="si">
              <IconMedal />
            </div>
            <div className="lbl">Certificates Earned</div>
            <div className="val">{certificates}</div>
            <div className="vsub">verifiable certificate</div>
          </Link>
          <div className="stat featured reveal" data-d="4">
            <div className="si">
              <IconPeople />
            </div>
            <div className="lbl">Research Team Eligibility</div>
            <div className="val">{eligibility}</div>
            <div className="vsub">courses completed</div>
          </div>
        </div>
      </div>
    </section>
  )
}
