import { useEffect, useRef, useState, type RefObject } from 'react'

import { getResearchTeamRequirements } from '../lib/api/public-research-team'
import type { ResearchTeamRequiredCourse } from '../lib/api/public-research-team'
import { probeSignedIn } from '../lib/auth-session-lazy'
import { usePageTitle } from '../lib/page-title'
import { GuestResearchTeam } from './research-team/ResearchTeamGuest'
import { MemberResearchTeam } from './research-team/ResearchTeamMember'
import type { ResearchTeamProgressView } from './research-team/ResearchTeamProgressPanel'
import './ResearchTeamPage.css'

function useReveal(rootRef: RefObject<HTMLElement | null>, watch: string) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const nodes = Array.from(root.querySelectorAll('.reveal'))
    if (typeof IntersectionObserver === 'undefined') {
      for (const el of nodes) el.classList.add('in')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('in')
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of nodes) observer.observe(el)
    return () => observer.disconnect()
  }, [rootRef, watch])
}

export default function ResearchTeamPage() {
  usePageTitle('Research Team')

  const rootRef = useRef<HTMLDivElement>(null)
  const [courses, setCourses] = useState<ResearchTeamRequiredCourse[] | null>(null)
  const [requirementsLoading, setRequirementsLoading] = useState(true)
  const [requirementsError, setRequirementsError] = useState<string | null>(null)
  const [progress, setProgress] = useState<ResearchTeamProgressView | null>(null)

  useReveal(
    rootRef,
    `${progress ? 'member' : 'guest'}:${courses?.length ?? 'pending'}:${requirementsLoading}`,
  )

  useEffect(() => {
    let cancelled = false

    void (async () => {
      setRequirementsLoading(true)
      setRequirementsError(null)
      try {
        const requirements = await getResearchTeamRequirements()
        if (!cancelled) setCourses(requirements.courses)
      } catch {
        if (!cancelled) {
          setCourses(null)
          setRequirementsError('Could not load eligibility requirements. Please try again later.')
        }
      } finally {
        if (!cancelled) setRequirementsLoading(false)
      }

      try {
        const signedIn = await probeSignedIn()
        if (!signedIn || cancelled) return
        const { getMyResearchTeam } = await import('../lib/api/research-team')
        const me = await getMyResearchTeam()
        if (!cancelled) setProgress(me)
      } catch {
        if (!cancelled) setProgress(null)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div ref={rootRef} className="pg-research" data-testid="student-page-research-team">
      {progress ? (
        <MemberResearchTeam progress={progress} />
      ) : (
        <GuestResearchTeam error={requirementsError} />
      )}
    </div>
  )
}
