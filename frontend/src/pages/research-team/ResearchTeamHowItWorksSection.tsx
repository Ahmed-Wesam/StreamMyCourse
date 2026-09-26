import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { researchTeamHowItWorks } from '../../lib/marketing/researchTeamCopy'

export function ResearchTeamHowItWorksSection() {
  return (
    <section className="px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={researchTeamHowItWorks.kicker}
              title={researchTeamHowItWorks.title}
              lead={researchTeamHowItWorks.lead}
            />
          </Reveal>
        </div>
        <div className="relative mx-auto grid max-w-[1000px] grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {researchTeamHowItWorks.steps.map((step, index) => (
            <Reveal key={step.title}>
              <div className="text-center">
                <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-rs-grad-cta text-lg font-extrabold text-white shadow-[0_14px_28px_-10px_rgba(30,94,255,.45)]">
                  {index + 1}
                </div>
                <h3 className="mb-2 text-lg font-extrabold tracking-tight text-rs-ink">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-rs-body">{step.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
