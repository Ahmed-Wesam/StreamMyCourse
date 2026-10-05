import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Field } from '../../components/ui/Field'
import { fetchMe } from '../../lib/api/session'
import {
  allowResearchTeamReapply,
  getResearchTeamApplication,
  patchResearchTeamApplicationStatus,
  type AdminResearchTeamApplication,
} from '../../lib/api/research-team-teacher'
import type { ResearchTeamApplicationStatus } from '../../lib/api/research-team'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { usePageTitle } from '../../lib/page-title'

const STATUS_OPTIONS: ResearchTeamApplicationStatus[] = [
  'submitted',
  'under_review',
  'accepted',
  'rejected',
]

function statusOptionLabel(status: ResearchTeamApplicationStatus): string {
  switch (status) {
    case 'under_review':
      return 'Under review'
    case 'accepted':
      return 'Accepted'
    case 'rejected':
      return 'Rejected'
    default:
      return 'Submitted'
  }
}

const RESEARCH_INTEREST_LABELS: Record<string, string> = {
  surgical_research: 'Surgical Research',
  systematic_reviews: 'Systematic Reviews',
  meta_analysis: 'Meta-Analysis',
  clinical_research: 'Clinical Research',
  database_research: 'Database Research',
}

function ResearchPreferences({ tags }: { tags: string[] | undefined }) {
  const labels = (tags ?? []).map((tag) => RESEARCH_INTEREST_LABELS[tag] ?? tag)
  if (labels.length === 0) return null
  return (
    <div className="mt-4">
      <p className="mb-1 text-sm font-bold text-rs-navy">Research preferences</p>
      <ul className="list-disc pl-5 text-sm text-rs-body">
        {labels.map((label) => (
          <li key={label}>{label}</li>
        ))}
      </ul>
    </div>
  )
}

export default function TeacherResearchTeamApplicationDetailPage() {
  usePageTitle('Research Team application')
  const { applicationId: applicationIdParam } = useParams<{ applicationId: string }>()
  const applicationId = applicationIdParam?.trim() ?? ''

  const [allowed, setAllowed] = useState<boolean | null>(null)
  const [application, setApplication] = useState<AdminResearchTeamApplication | null>(null)
  const [statusDraft, setStatusDraft] = useState<ResearchTeamApplicationStatus>('submitted')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!applicationId) {
        setError('Missing application id.')
        setAllowed(false)
        setLoading(false)
        return
      }
      try {
        const me = await fetchMe()
        if (cancelled) return
        if (me.role.toLowerCase() !== 'admin') {
          setAllowed(false)
          setLoading(false)
          return
        }
        setAllowed(true)
        const row = await getResearchTeamApplication(applicationId)
        if (!cancelled) {
          setApplication(row)
          setStatusDraft(row.status)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setApplication(null)
          setError(catalogApiUserMessage(err))
          setAllowed((prev) => (prev === true ? true : false))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [applicationId])

  const handleStatusSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!applicationId || !application || busy) return
    try {
      setBusy(true)
      setError(null)
      const updated = await patchResearchTeamApplicationStatus(applicationId, statusDraft)
      setApplication(updated)
      setStatusDraft(updated.status)
    } catch (err) {
      setError(catalogApiUserMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const handleAllowReapply = async () => {
    if (!applicationId || busy) return
    try {
      setBusy(true)
      setError(null)
      const updated = await allowResearchTeamReapply(applicationId)
      setApplication(updated)
      setStatusDraft(updated.status)
    } catch (err) {
      setError(catalogApiUserMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading || allowed === null) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-muted sm:px-6">
        Loading application…
      </div>
    )
  }

  if (allowed === false && !error) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-ink sm:px-6">
        <Card className="p-8 text-center">
          <h1 className="text-xl font-extrabold text-rs-navy">Admin only</h1>
          <p className="mt-2 text-rs-body">
            You do not have access to Research Team application review.
          </p>
        </Card>
      </div>
    )
  }

  if (!application) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-ink sm:px-6">
        <Link
          to="/research-team/applications"
          className="mb-4 inline-block text-sm font-semibold text-rs-blue hover:underline"
        >
          ← Back to applications
        </Link>
        <Card className="p-6">
          <p className="text-rs-body" role="alert">
            {error ?? 'Application not found.'}
          </p>
        </Card>
      </div>
    )
  }

  const showAllowReapply = application.status === 'rejected' && application.reapplyAllowed === false

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
      <Link
        to="/research-team/applications"
        className="mb-4 inline-block text-sm font-semibold text-rs-blue hover:underline"
      >
        ← Back to applications
      </Link>

      <h1 className="mb-2 text-3xl font-extrabold tracking-tight text-rs-navy">
        {application.fullName || 'Applicant'}
      </h1>
      <p className="mb-6 text-sm text-rs-body">{application.email}</p>

      {error ? (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      ) : null}

      <Card className="mb-6 p-6">
        <h2 className="mb-4 text-xl font-extrabold text-rs-navy">Application</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-bold text-rs-navy">Country</dt>
            <dd className="text-rs-body">{application.country || '—'}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Institution</dt>
            <dd className="text-rs-body">{application.institution || '—'}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Position</dt>
            <dd className="text-rs-body">{application.position || '—'}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Weekly hours</dt>
            <dd className="text-rs-body">{application.weeklyHours || '—'}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Publications</dt>
            <dd className="text-rs-body">{application.publicationCount}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Projects</dt>
            <dd className="text-rs-body">{application.projectCount}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Stats experience</dt>
            <dd className="text-rs-body">{application.statsExperience}</dd>
          </div>
          <div>
            <dt className="font-bold text-rs-navy">Systematic review experience</dt>
            <dd className="text-rs-body">{application.sysReviewExperience}</dd>
          </div>
        </dl>

        <ResearchPreferences tags={application.researchInterestTags} />

        {application.researchAreas.length > 0 ? (
          <div className="mt-4">
            <p className="mb-1 text-sm font-bold text-rs-navy">Research areas</p>
            <p className="text-sm text-rs-body">{application.researchAreas.join(', ')}</p>
          </div>
        ) : null}

        <div className="mt-4">
          <p className="mb-1 text-sm font-bold text-rs-navy">Interests</p>
          <p className="whitespace-pre-wrap text-sm text-rs-body">{application.interests}</p>
        </div>

        <div className="mt-4">
          <p className="mb-1 text-sm font-bold text-rs-navy">Motivation</p>
          <p className="whitespace-pre-wrap text-sm text-rs-body">{application.motivation}</p>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="mb-4 text-xl font-extrabold text-rs-navy">Review</h2>
        <form onSubmit={(e) => void handleStatusSubmit(e)} className="space-y-4">
          <Field label="Status">
            <select
              aria-label="Status"
              value={statusDraft}
              onChange={(e) => setStatusDraft(e.target.value as ResearchTeamApplicationStatus)}
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {statusOptionLabel(status)}
                </option>
              ))}
            </select>
          </Field>
          <Button type="submit" disabled={busy} className="min-h-11">
            {busy ? 'Saving…' : 'Update status'}
          </Button>
        </form>

        {showAllowReapply ? (
          <div className="mt-6 border-t border-rs-line pt-6">
            <Button
              type="button"
              variant="ghost"
              className="min-h-11"
              disabled={busy}
              onClick={() => void handleAllowReapply()}
            >
              Allow reapply
            </Button>
          </div>
        ) : null}
      </Card>
    </div>
  )
}
