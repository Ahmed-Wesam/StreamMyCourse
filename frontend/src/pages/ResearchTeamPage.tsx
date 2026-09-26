import { usePageTitle } from '../lib/page-title'
import { ResearchTeamAuthorshipSection } from './research-team/ResearchTeamAuthorshipSection'
import { ResearchTeamEligibilitySection } from './research-team/ResearchTeamEligibilitySection'
import { ResearchTeamHeroSection } from './research-team/ResearchTeamHeroSection'
import { ResearchTeamHowItWorksSection } from './research-team/ResearchTeamHowItWorksSection'
import { ResearchTeamProjectsSection } from './research-team/ResearchTeamProjectsSection'
import { ResearchTeamWhyJoinSection } from './research-team/ResearchTeamWhyJoinSection'

export default function ResearchTeamPage() {
  usePageTitle('Research Team')

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-research-team">
      <ResearchTeamHeroSection />
      <ResearchTeamWhyJoinSection />
      <ResearchTeamProjectsSection />
      <ResearchTeamAuthorshipSection />
      <ResearchTeamHowItWorksSection />
      <ResearchTeamEligibilitySection />
    </div>
  )
}
