import { Link } from 'react-router-dom'

import { IconArrow } from './dashboardIcons'

const OWNED_SUBTITLE =
  'Continue your courses, track your progress, and manage your learning journey.'
const EMPTY_SUBTITLE =
  'Your account is set up and ready. Browse the course catalog and enroll in your first course to get started.'

type StudentDashboardHeroProps = {
  givenName: string | null
  familyName: string | null
  showBrowse: boolean
}

function welcomeLabel(givenName: string | null): string {
  const first = givenName?.trim().split(/\s+/)[0]
  if (!first) return 'Welcome back'
  return `Welcome back, ${first.charAt(0).toUpperCase()}${first.slice(1)}`
}

function avatarMark(givenName: string | null, familyName: string | null): string {
  const parts = [givenName, familyName]
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part))
  if (parts.length === 0) return '?'
  return parts
    .map((part) => part.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function StudentDashboardHero({ givenName, familyName, showBrowse }: StudentDashboardHeroProps) {
  return (
    <section className="dash-hero">
      <div className="wrap">
        <span className="dash-hi reveal">
          <span className="avatar">{avatarMark(givenName, familyName)}</span> {welcomeLabel(givenName)}
        </span>
        <h1 className="reveal" data-d="1">
          Student Dashboard
        </h1>
        <p className="sub reveal" data-d="2">
          {showBrowse ? EMPTY_SUBTITLE : OWNED_SUBTITLE}
        </p>
        {showBrowse ? (
          <div className="dash-browse-cta" style={{ display: 'inline-flex', gap: 12, marginTop: 24, flexWrap: 'wrap' }}>
            <Link to="/courses#courses-catalog" className="btn btn-primary" style={{ fontSize: 15, padding: '12px 24px' }}>
              Explore Courses <IconArrow />
            </Link>
          </div>
        ) : null}
      </div>
    </section>
  )
}
