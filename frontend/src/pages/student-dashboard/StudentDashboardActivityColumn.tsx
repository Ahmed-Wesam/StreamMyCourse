import { Link } from 'react-router-dom'

import type { LearningActivityItem } from '../../lib/api/activity'
import { IconArrow, IconBook, IconCheck, IconMedal } from './dashboardIcons'

export type DashboardCertificateCard = {
  id: string
  courseTitle: string
  issueDate: string
}

type StudentDashboardActivityColumnProps = {
  available: boolean
  items: LearningActivityItem[]
  courseTitles: Record<string, string>
  certificates: DashboardCertificateCard[] | null
  pathwayCount: number
}

const EMPTY_ACTIVITY =
  'No activity yet. Start a course to see your progress here.'

function activityHeading(item: LearningActivityItem): string {
  switch (item.kind) {
    case 'lesson_completion':
      return `Completed Lesson · ${item.title}`
    case 'quiz_attempt':
      return `Completed Quiz · ${item.title}`
    case 'assignment_submission':
      return `Submitted Assignment · ${item.title}`
    case 'certificate':
      return 'Certificate Earned'
    default:
      return item.title
  }
}

function activityDetail(item: LearningActivityItem, courseTitles: Record<string, string>): string {
  if (item.kind === 'certificate') return item.title
  return courseTitles[item.courseId] ?? ''
}

function activityHref(item: LearningActivityItem): string | null {
  if (item.kind === 'lesson_completion' && item.courseId && item.resourceId) {
    return `/courses/${item.courseId}/lessons/${item.resourceId}`
  }
  if (item.kind === 'certificate') return '/certificates'
  return null
}

function activityIcon(item: LearningActivityItem) {
  if (item.kind === 'quiz_attempt') return { className: 'ai green', node: <IconCheck strokeWidth={2.6} /> }
  if (item.kind === 'certificate') return { className: 'ai gold', node: <IconMedal /> }
  if (item.kind === 'assignment_submission') return { className: 'ai', node: <IconArrow strokeWidth={2} /> }
  return { className: 'ai', node: <IconBook /> }
}

function formatActivityWhen(iso: string, now = Date.now()): string {
  const at = Date.parse(iso)
  if (Number.isNaN(at)) return ''
  const diff = now - at
  const hour = 60 * 60 * 1000
  const day = 24 * hour
  if (diff < hour) return 'Just now'
  if (diff < day) {
    const hours = Math.floor(diff / hour)
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  }
  const days = Math.floor(diff / day)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  const weeks = Math.floor(days / 7)
  if (weeks === 1) return '1 week ago'
  if (weeks < 8) return `${weeks} weeks ago`
  return new Date(at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function certificateNote(count: number, pathwayCount: number): string | null {
  if (count === 0) return 'Complete courses to unlock certificates.'
  if (pathwayCount > 0 && count >= pathwayCount) return null
  return 'Complete more courses to unlock additional certificates.'
}

export function StudentDashboardActivityColumn({
  available,
  items,
  courseTitles,
  certificates,
  pathwayCount,
}: StudentDashboardActivityColumnProps) {
  const rows = available ? items : []
  const certs = certificates ?? []
  const note = certificateNote(certs.length, pathwayCount)

  return (
    <section className="db">
      <div className="wrap">
        <div className="split">
          <div>
            <div className="db-head">
              <div className="ht">
                <h2>Recent Activity</h2>
                <span className="htmeta">Your latest progress across courses</span>
              </div>
            </div>
            <div className="act reveal">
              <ul>
                {rows.length === 0 ? (
                  <li
                    style={{
                      justifyContent: 'center',
                      padding: 18,
                      color: 'var(--muted)',
                      fontSize: 14,
                      fontWeight: 600,
                      textAlign: 'center',
                      width: '100%',
                    }}
                  >
                    {EMPTY_ACTIVITY}
                  </li>
                ) : (
                  rows.map((item) => {
                    const icon = activityIcon(item)
                    const href = activityHref(item)
                    const heading = activityHeading(item)
                    const detail = activityDetail(item, courseTitles)
                    return (
                      <li key={`${item.kind}-${item.resourceId}-${item.at}`}>
                        <div className={icon.className}>{icon.node}</div>
                        <div className="at">
                          {href ? (
                            <Link to={href} className="h">
                              {heading}
                            </Link>
                          ) : (
                            <div className="h">{heading}</div>
                          )}
                          {detail ? <div className="d">{detail}</div> : null}
                          <div className="tm">{formatActivityWhen(item.at)}</div>
                        </div>
                      </li>
                    )
                  })
                )}
              </ul>
            </div>
          </div>

          <div>
            <div className="db-head">
              <div className="ht">
                <h2>Your Certificates</h2>
                <span className="htmeta">Verifiable certificates of completion</span>
              </div>
            </div>
            <div className="certs reveal" data-d="1">
              {certs.map((certificate) => (
                <Link key={certificate.id} to="/certificates" className="cert-mini">
                  <div className="seal">
                    <IconMedal strokeWidth={2.2} />
                  </div>
                  <div className="info">
                    <h4>{certificate.courseTitle}</h4>
                    <div className="date">{certificate.issueDate || 'Certificate Earned'}</div>
                  </div>
                </Link>
              ))}
              {note ? <div className="cert-empty">{note}</div> : null}
              <Link to="/certificates" className="btn btn-ghost">
                View All Certificates
                <IconArrow />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
