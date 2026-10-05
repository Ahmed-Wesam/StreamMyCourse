import { Link } from 'react-router-dom'

export type ResearchTeamProgressView = {
  courses: Array<{ courseId: string; title: string; certified: boolean }>
  eligible: boolean
  canSubmit: boolean
  application: { status: string; reapplyAllowed: boolean } | null
}

type ResearchTeamProgressPanelProps = {
  progress: ResearchTeamProgressView
}

function statusLabel(status: string): string {
  switch (status) {
    case 'submitted':
      return 'Your application has been submitted.'
    case 'under_review':
      return 'Your application is under review.'
    case 'accepted':
      return 'Your application has been accepted.'
    case 'rejected':
      return 'Your application was rejected.'
    default:
      return status
  }
}

export function ResearchTeamProgressPanel({ progress }: ResearchTeamProgressPanelProps) {
  const total = progress.courses.length
  const certified = progress.courses.filter((course) => course.certified).length
  const application = progress.application
  const applicationsClosed = total === 0
  const showReapplyHint =
    !applicationsClosed &&
    progress.canSubmit &&
    application?.status === 'rejected' &&
    application.reapplyAllowed === true
  const showUnlockGuidance =
    !applicationsClosed &&
    !progress.canSubmit &&
    !progress.eligible &&
    (!application || application.status === 'rejected')

  return (
    <div className="rt-app-body" data-testid="research-team-progress">
      {applicationsClosed ? (
        <p>
          Applications are not open yet. Required courses have not been published for the Research
          Team pathway.
        </p>
      ) : (
        <p>
          {certified} of {total} certificates
        </p>
      )}

      {application && !applicationsClosed ? (
        <p data-testid="research-team-status">{statusLabel(application.status)}</p>
      ) : null}

      {showReapplyHint ? <p>You may apply again.</p> : null}

      {progress.canSubmit ? (
        <div className="rt-app-actions">
          <Link to="/research-team/apply" className="btn btn-primary btn-sm">
            Apply To Research Team
          </Link>
        </div>
      ) : null}

      {showUnlockGuidance ? (
        <p>
          Complete the required certificates to unlock the application.{' '}
          <Link to="/courses">Explore courses</Link>
        </p>
      ) : null}
    </div>
  )
}
