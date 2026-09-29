import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Card } from '../../components/ui/Card'
import { getMyResearchTeam } from '../../lib/api/research-team'

export function StudentDashboardResearchTeamBlock() {
  const [summary, setSummary] = useState<{ certified: number; total: number } | null>(null)
  const [closed, setClosed] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const me = await getMyResearchTeam()
        if (cancelled) return
        if (me.courses.length === 0) {
          setClosed(true)
          setSummary(null)
          return
        }
        const certified = me.courses.filter((course) => course.certified).length
        setClosed(false)
        setSummary({ certified, total: me.courses.length })
      } catch {
        if (!cancelled) {
          setSummary(null)
          setClosed(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!summary && !closed) return null

  return (
    <Card
      className="rounded-rs-lg border border-rs-line px-5 py-4 shadow-rs-sm"
      data-testid="student-dashboard-research-team"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-rs-muted">Research Team</p>
      {closed ? (
        <p className="mt-1 text-sm font-semibold text-rs-ink">Applications are not open yet.</p>
      ) : (
        <p className="mt-1 text-sm font-semibold text-rs-ink">
          {summary!.certified} of {summary!.total} certificates
        </p>
      )}
      <Link
        to="/research-team"
        className="mt-3 inline-flex min-h-11 items-center text-sm font-bold text-rs-blue underline-offset-2 hover:underline"
      >
        View Research Team
      </Link>
    </Card>
  )
}
