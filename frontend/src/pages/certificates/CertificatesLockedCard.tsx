import { Link } from 'react-router-dom'

import { CourseSealIcon } from './CourseSealIcon'
import { sealKeyForTitle } from './courseCertificateMeta'

export type LockedCertificateRow = {
  courseId: string
  title: string
  owned: boolean
  progressPct: number
  exploreHref: string
}

type CertificatesLockedCardProps = {
  row: LockedCertificateRow
  revealDelay?: number
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export function CertificatesLockedCard({ row, revealDelay }: CertificatesLockedCardProps) {
  const sealKey = sealKeyForTitle(row.title)
  const owned = row.owned
  const pct = Math.max(0, Math.min(100, Math.round(row.progressPct)))

  return (
    <article className="cert-lock-card reveal" {...(revealDelay ? { 'data-d': String(revealDelay) } : {})}>
      <CourseSealIcon sealKey={sealKey} variant="locked" />
      <p className="cl-eyebrow">Certificate of Completion</p>
      <h3 className="cl-title">{row.title}</h3>
      {owned ? (
        <span className="cl-status in-progress">{pct > 0 ? `${pct}% Complete` : 'Enrolled — Not Started'}</span>
      ) : (
        <span className="cl-status not-started">Not Yet Enrolled</span>
      )}
      {owned ? (
        <div className="cl-prog">
          <div className="cl-pct-row">
            <span>Progress</span>
            <b>{pct}%</b>
          </div>
          <div className="cl-bar">
            <i style={{ width: `${pct}%` }} />
          </div>
        </div>
      ) : null}
      {owned ? (
        <Link to="/dashboard" className="btn btn-primary">
          Continue Course
          <ArrowIcon />
        </Link>
      ) : (
        <Link to={row.exploreHref} className="btn btn-ghost">
          Explore Course
          <ArrowIcon />
        </Link>
      )}
    </article>
  )
}
