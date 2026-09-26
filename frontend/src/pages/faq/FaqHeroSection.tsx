import { Check } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Eyebrow } from '../../components/ui/Eyebrow'
import { Reveal } from '../../components/ui/Reveal'
import { faqHero } from '../../lib/marketing/faqCopy'

export function FaqHeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 py-16 sm:px-7 sm:py-[68px]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_10%,rgba(58,134,255,.11),transparent_62%),radial-gradient(500px_360px_at_0%_50%,rgba(30,94,255,.06),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40 [background-image:radial-gradient(rgba(30,94,255,.10)_1px,transparent_1px)] [background-size:30px_30px] [mask-image:radial-gradient(680px_480px_at_25%_35%,#000,transparent_72%)]"
      />

      <div className="relative mx-auto grid max-w-wrap items-center gap-12 nav:grid-cols-[1.15fr_0.85fr] nav:gap-[60px]">
        <div>
          <Reveal>
            <Eyebrow>{faqHero.eyebrow}</Eyebrow>
          </Reveal>
          <Reveal>
            <h1 className="mt-4 text-[clamp(36px,4.8vw,56px)] font-extrabold leading-[1.06] tracking-tight text-rs-ink">
              {faqHero.titleLine1}
              <br />
              <span className="bg-rs-grad-cta bg-clip-text text-transparent">
                {faqHero.titleHighlight}
              </span>
            </h1>
          </Reveal>
          <Reveal>
            <p className="mt-5 max-w-[540px] text-[17.5px] leading-relaxed text-rs-body">
              {faqHero.sub}
            </p>
          </Reveal>
          <Reveal>
            <ul className="mt-7 space-y-2.5">
              {faqHero.trustItems.map((item) => (
                <li key={item} className="flex items-center gap-2.5 text-[14.5px] font-semibold text-rs-ink">
                  <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-rs-sky text-rs-blue">
                    <Check size={13} strokeWidth={2.8} aria-hidden />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal>
            <div className="mt-[30px] flex flex-wrap gap-3.5">
              <Button to="/courses" arrow>
                {faqHero.primaryCta}
              </Button>
              <Button to="/contact" variant="ghost">
                {faqHero.contactCta}
              </Button>
            </div>
          </Reveal>
        </div>

        <Reveal>
          <Card className="relative overflow-hidden rounded-rs-lg px-7 py-8 shadow-rs-lg">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(420px_200px_at_50%_0%,rgba(30,94,255,.04),transparent)]"
            />
            <div className="relative space-y-4">
              <p className="text-[15px] font-extrabold tracking-tight text-rs-ink">
                {faqHero.supportCard.title}
              </p>
              {faqHero.supportCard.rows.map((row, index) => (
                <div
                  key={row.label}
                  className={[
                    'flex items-center justify-between gap-3 py-2.5 text-[13.5px]',
                    index < faqHero.supportCard.rows.length - 1 ? 'border-b border-rs-line' : '',
                  ].join(' ')}
                >
                  <span className="font-semibold text-rs-muted">{row.label}</span>
                  {'pill' in row && row.pill ? (
                    <span className="rounded-full bg-rs-sky px-2.5 py-1 text-[12px] font-extrabold text-rs-blue">
                      {row.value}
                    </span>
                  ) : (
                    <span className="font-bold text-rs-ink">{row.value}</span>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  )
}
