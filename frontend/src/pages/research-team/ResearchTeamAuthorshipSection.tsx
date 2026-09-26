import { Check, TrendingUp } from 'lucide-react'

import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { researchTeamAuthorship } from '../../lib/marketing/researchTeamCopy'

export function ResearchTeamAuthorshipSection() {
  return (
    <section className="bg-rs-sky-2/40 px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={researchTeamAuthorship.kicker}
              title={researchTeamAuthorship.title}
              lead={researchTeamAuthorship.lead}
            />
          </Reveal>
        </div>
        <Reveal>
          <Card className="rounded-rs-lg p-8 shadow-rs-sm sm:p-9">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-[13px] border border-[#e2ebff] bg-rs-grad-soft text-rs-blue">
                <Check aria-hidden className="size-5" strokeWidth={2.2} />
              </div>
              <h3 className="text-lg font-extrabold tracking-tight text-rs-ink">
                {researchTeamAuthorship.contributionsHeading}
              </h3>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {researchTeamAuthorship.contributions.map((item) => (
                <div
                  key={item}
                  className="flex items-start gap-2.5 rounded-[14px] border border-rs-line-2 bg-rs-sky-2/60 px-4 py-3 text-sm font-semibold text-rs-ink"
                >
                  <Check
                    aria-hidden
                    className="mt-0.5 size-4 shrink-0 text-rs-blue"
                    strokeWidth={2.4}
                  />
                  {item}
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-rs border border-rs-line-2 bg-white px-5 py-5">
              <h4 className="mb-2 flex items-center gap-2 text-[15px] font-extrabold text-rs-ink">
                <TrendingUp aria-hidden className="size-[17px] text-rs-blue" strokeWidth={2} />
                {researchTeamAuthorship.growthTitle}
              </h4>
              <p className="text-sm leading-relaxed text-rs-body">
                {researchTeamAuthorship.growthBody}
              </p>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  )
}
