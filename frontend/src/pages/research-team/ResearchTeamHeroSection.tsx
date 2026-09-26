import { Check, Medal, Star } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Eyebrow } from '../../components/ui/Eyebrow'
import { Reveal } from '../../components/ui/Reveal'
import { researchTeamHero } from '../../lib/marketing/researchTeamCopy'

export function ResearchTeamHeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 py-16 sm:px-7 sm:py-[68px]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_10%,rgba(58,134,255,.12),transparent_62%),radial-gradient(500px_360px_at_0%_40%,rgba(30,94,255,.06),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-45 [background-image:radial-gradient(rgba(30,94,255,.10)_1px,transparent_1px)] [background-size:30px_30px] [mask-image:radial-gradient(680px_480px_at_25%_30%,#000,transparent_72%)]"
      />

      <div className="relative mx-auto grid max-w-wrap items-center gap-9 nav:grid-cols-[1.1fr_0.9fr] nav:gap-[60px]">
        <div>
          <Reveal>
            <Eyebrow>{researchTeamHero.eyebrow}</Eyebrow>
          </Reveal>
          <Reveal>
            <h1 className="mt-4 text-[clamp(36px,5vw,58px)] font-extrabold leading-[1.05] tracking-tight text-rs-ink">
              {researchTeamHero.titleBefore}{' '}
              <span className="bg-rs-grad-cta bg-clip-text text-transparent">
                {researchTeamHero.titleHighlight}
              </span>
              <br />
              {researchTeamHero.titleAfter}
            </h1>
          </Reveal>
          <Reveal>
            <p className="mt-5 max-w-[520px] text-lg leading-relaxed text-rs-body">
              {researchTeamHero.sub}
            </p>
          </Reveal>
          <Reveal>
            <div className="mt-[30px] flex flex-wrap gap-3.5">
              <Button to="/courses" arrow>
                {researchTeamHero.primaryCta}
              </Button>
              <Button href="#eligibility" variant="ghost">
                {researchTeamHero.secondaryCta}
              </Button>
            </div>
          </Reveal>
        </div>

        <Reveal>
          <Card className="relative overflow-hidden rounded-rs-lg p-7 shadow-rs-lg">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(420px_200px_at_100%_0%,rgba(30,94,255,.04),transparent)]"
            />
            <div className="relative">
              <h3 className="mb-2.5 text-sm font-bold uppercase tracking-[0.08em] text-rs-muted">
                {researchTeamHero.cardTitle}
              </h3>
              <p className="mb-5 text-sm leading-relaxed text-rs-body">
                {researchTeamHero.cardBody}
              </p>
              <ul className="mb-5 space-y-2.5">
                {researchTeamHero.pathwaySteps.map((step, index) => {
                  const isCert = index === 4
                  const isGoal = index === 5
                  return (
                    <li key={step} className="flex items-center gap-2.5 text-sm font-semibold text-rs-ink">
                      <span
                        className={[
                          'flex size-7 shrink-0 items-center justify-center rounded-full border',
                          isGoal
                            ? 'border-[#f3df9a] bg-[#fff5d6] text-[#a96b00]'
                            : isCert
                              ? 'border-[#bce7c8] bg-[#dcf5e3] text-[#0d6f3e]'
                              : 'border-[#e2ebff] bg-rs-grad-soft text-rs-blue',
                        ].join(' ')}
                      >
                        {isGoal ? (
                          <Star aria-hidden className="size-3.5" strokeWidth={2.2} />
                        ) : isCert ? (
                          <Medal aria-hidden className="size-3.5" strokeWidth={2.2} />
                        ) : (
                          <Check aria-hidden className="size-3.5" strokeWidth={2.6} />
                        )}
                      </span>
                      <span className={isGoal ? 'text-rs-blue' : undefined}>{step}</span>
                    </li>
                  )
                })}
              </ul>
              <Button to="/courses" size="sm" className="w-full justify-center">
                {researchTeamHero.primaryCta}
              </Button>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  )
}
