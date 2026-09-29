import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Card } from '../../components/ui/Card'
import { fetchMe } from '../../lib/api/session'
import {
  listResearchTeamApplications,
  type AdminResearchTeamApplication,
} from '../../lib/api/research-team-teacher'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { usePageTitle } from '../../lib/page-title'

function statusLabel(status: AdminResearchTeamApplication['status']): string {
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

export default function TeacherResearchTeamApplicationsPage() {
  usePageTitle('Research Team applications')
  const [allowed, setAllowed] = useState<boolean | null>(null)
  const [applications, setApplications] = useState<AdminResearchTeamApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const me = await fetchMe()
        if (cancelled) return
        if (me.role.toLowerCase() !== 'admin') {
          setAllowed(false)
          setLoading(false)
          return
        }
        setAllowed(true)
        const data = await listResearchTeamApplications()
        if (!cancelled) {
          setApplications(data.applications)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(catalogApiUserMessage(err))
          setApplications([])
          setAllowed((prev) => (prev === true ? true : false))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading || allowed === null) {
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
        <h1 className="mb-6 text-3xl font-extrabold tracking-tight text-rs-navy">
          Research Team applications
        </h1>
        <p className="text-sm text-rs-muted">Loading applications…</p>
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

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
      <h1 className="mb-6 text-3xl font-extrabold tracking-tight text-rs-navy">
        Research Team applications
      </h1>

      {error ? (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      ) : null}

      {!error && applications.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm text-rs-body">No applications yet.</p>
        </Card>
      ) : null}

      {!error && applications.length > 0 ? (
        <ul className="space-y-3">
          {applications.map((app) => (
            <li key={app.id}>
              <Card className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <Link
                      to={`/research-team/applications/${encodeURIComponent(app.id)}`}
                      className="text-lg font-extrabold text-rs-navy hover:underline"
                    >
                      {app.fullName || 'Unnamed applicant'}
                    </Link>
                    <p className="mt-1 text-sm text-rs-body">
                      {statusLabel(app.status)}
                      {app.email ? ` · ${app.email}` : ''}
                    </p>
                  </div>
                  <Link
                    to={`/research-team/applications/${encodeURIComponent(app.id)}`}
                    className="inline-flex min-h-11 items-center rounded-[10px] px-4 text-sm font-bold text-rs-blue hover:bg-rs-sky-2"
                  >
                    Review
                  </Link>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
