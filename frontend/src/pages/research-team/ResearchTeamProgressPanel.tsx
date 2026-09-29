import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'

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
    <Card
      className="mx-auto mb-8 max-w-[900px] rounded-rs px-6 py-5 shadow-rs-sm"
      data-testid="research-team-progress"
    >
      {applicationsClosed ? (
        <p className="text-sm leading-relaxed text-rs-body">
          Applications are not open yet. Required courses have not been published for the Research
          Team pathway.
        </p>
      ) : (
        <p className="text-sm font-semibold text-rs-ink">
          {certified} of {total} certificates
        </p>
      )}

      {application && !applicationsClosed ? (
        <p className="mt-2 text-sm leading-relaxed text-rs-body" data-testid="research-team-status">
          {statusLabel(application.status)}
        </p>
      ) : null}

      {showReapplyHint ? (
        <p className="mt-2 text-sm font-semibold text-rs-blue">You may apply again.</p>
      ) : null}

      {progress.canSubmit ? (
        <div className="mt-4">
          <Button to="/research-team/apply" size="sm">
            Apply
          </Button>
        </div>
      ) : null}

      {showUnlockGuidance ? (
        <p className="mt-2 text-sm text-rs-muted">
          Complete the required certificates to unlock the application.{' '}
          <Link to="/courses" className="font-semibold text-rs-blue underline-offset-2 hover:underline">
            Explore courses
          </Link>
        </p>
      ) : null}
    </Card>
  )
}
