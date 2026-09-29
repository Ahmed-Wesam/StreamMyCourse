import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { aboutFinalCta } from '../../lib/marketing/aboutCopy'

export function AboutFinalCtaSection() {
  return (
    <section className="px-5 pb-[100px] pt-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="relative overflow-hidden rounded-rs-lg bg-rs-grad px-6 py-10 text-center shadow-rs-lg sm:px-12 sm:[padding-block:60px]">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(800px_360px_at_100%_0%,rgba(255,255,255,.12),transparent)]"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 [background-image:radial-gradient(rgba(255,255,255,.08)_1px,transparent_1px)] [background-size:28px_28px]"
            />
            <div className="relative">
              <p className="mb-4 text-[13px] font-bold uppercase tracking-[0.12em] text-white/70">
                {aboutFinalCta.kicker}
              </p>
              <h2 className="text-[clamp(26px,3.8vw,40px)] font-extrabold leading-tight tracking-tight text-white">
                {aboutFinalCta.title}
              </h2>
              <p className="mx-auto mt-4 max-w-[560px] text-[17px] leading-relaxed text-white/85">
                {aboutFinalCta.lead}
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Button to="/courses" arrow variant="onDark">
                  {aboutFinalCta.primaryCta}
                </Button>
                <Button href="#story" variant="ghostOnDark">
                  {aboutFinalCta.secondaryCta}
                </Button>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
