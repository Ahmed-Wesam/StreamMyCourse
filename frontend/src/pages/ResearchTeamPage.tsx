import { useEffect, useState } from 'react'

import { getResearchTeamRequirements } from '../lib/api/public-research-team'
import type { ResearchTeamRequiredCourse } from '../lib/api/public-research-team'
import { probeSignedIn } from '../lib/auth-session-lazy'
import { usePageTitle } from '../lib/page-title'
import { ResearchTeamAuthorshipSection } from './research-team/ResearchTeamAuthorshipSection'
import { ResearchTeamEligibilitySection } from './research-team/ResearchTeamEligibilitySection'
import { ResearchTeamHeroSection } from './research-team/ResearchTeamHeroSection'
import { ResearchTeamHowItWorksSection } from './research-team/ResearchTeamHowItWorksSection'
import {
  ResearchTeamProgressPanel,
  type ResearchTeamProgressView,
} from './research-team/ResearchTeamProgressPanel'
import { ResearchTeamProjectsSection } from './research-team/ResearchTeamProjectsSection'
import { ResearchTeamWhyJoinSection } from './research-team/ResearchTeamWhyJoinSection'

export default function ResearchTeamPage() {
  usePageTitle('Research Team')

  const [courses, setCourses] = useState<ResearchTeamRequiredCourse[] | null>(null)
  const [requirementsLoading, setRequirementsLoading] = useState(true)
  const [requirementsError, setRequirementsError] = useState<string | null>(null)
  const [progress, setProgress] = useState<ResearchTeamProgressView | null>(null)

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
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-research-team">
      <ResearchTeamHeroSection />
      <ResearchTeamWhyJoinSection />
      <ResearchTeamProjectsSection />
      <ResearchTeamAuthorshipSection />
      <ResearchTeamHowItWorksSection />
      {progress ? (
        <div className="bg-rs-sky-2/40 px-5 pt-10 sm:px-7">
          <ResearchTeamProgressPanel progress={progress} />
        </div>
      ) : null}
      <ResearchTeamEligibilitySection
        courses={courses}
        loading={requirementsLoading}
        error={requirementsError}
      />
    </div>
  )
}
