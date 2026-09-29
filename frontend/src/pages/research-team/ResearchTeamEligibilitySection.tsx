import { BookOpen, Info } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { ResearchTeamRequiredCourse } from '../../lib/api/public-research-team'
import { researchTeamEligibility } from '../../lib/marketing/researchTeamCopy'

type ResearchTeamEligibilitySectionProps = {
  courses: ResearchTeamRequiredCourse[] | null
  loading?: boolean
  error?: string | null
}

export function ResearchTeamEligibilitySection({
  courses,
  loading = false,
  error = null,
}: ResearchTeamEligibilitySectionProps) {
  const showEmpty = !loading && !error && courses !== null && courses.length === 0
  const showCourses = !loading && !error && courses !== null && courses.length > 0

  return (
    <section id="eligibility" className="scroll-mt-24 bg-rs-sky-2/40 px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={researchTeamEligibility.kicker}
              title={researchTeamEligibility.title}
              lead={researchTeamEligibility.lead}
            />
          </Reveal>
        </div>

        {loading ? (
          <p className="mx-auto max-w-[900px] text-center text-sm text-rs-body">
            Loading requirements…
          </p>
        ) : null}

        {error ? (
          <p className="mx-auto max-w-[900px] text-center text-sm font-semibold text-[#b91c1c]">
            {error}
          </p>
        ) : null}

        {showEmpty ? (
          <Reveal className="mx-auto max-w-[900px]">
            <Card
              className="rounded-rs px-6 py-5 text-center shadow-rs-sm"
              data-testid="research-team-applications-closed"
            >
              <p className="text-sm font-semibold text-rs-ink">
                Applications are not open yet. Required courses will appear here when available.
              </p>
            </Card>
          </Reveal>
        ) : null}

        {showCourses ? (
          <div className="mx-auto grid max-w-[900px] grid-cols-1 gap-4 sm:grid-cols-2">
            {courses.map((course) => (
              <Reveal key={course.id}>
                <Card
                  className="rounded-rs px-6 py-5 shadow-rs-sm"
                  data-testid="research-team-required-course"
                >
                  <div className="mb-3 flex size-11 items-center justify-center rounded-[13px] border border-[#e2ebff] bg-rs-grad-soft text-rs-blue">
                    <BookOpen aria-hidden className="size-5" strokeWidth={2} />
                  </div>
                  <h3 className="text-base font-extrabold tracking-tight text-rs-ink">
                    {course.title}
                  </h3>
                </Card>
              </Reveal>
            ))}
          </div>
        ) : null}

        {showCourses ? (
          <Reveal className="mx-auto mt-6 max-w-[900px]">
            <Card className="rounded-rs px-6 py-5 shadow-rs-sm">
              <p className="text-sm font-semibold text-rs-ink">
                {researchTeamEligibility.certificateNote}
              </p>
            </Card>
          </Reveal>
        ) : null}

        <Reveal className="mx-auto mt-5 max-w-[900px]">
          <div className="flex items-start gap-2.5 rounded-rs border border-rs-line-2 bg-white px-5 py-4 text-sm leading-relaxed text-rs-body">
            <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-rs-blue" strokeWidth={2} />
            {researchTeamEligibility.note}
          </div>
        </Reveal>

        <div className="mt-8 text-center">
          <Reveal>
            <Button to="/courses" arrow>
              {researchTeamEligibility.primaryCta}
            </Button>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
