import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { coursesCatalogHero } from '../../lib/marketing/coursesCatalogCopy'

export function CoursesCatalogHeroSection() {
  return (
    <section className="relative overflow-hidden px-5 py-[60px] text-center sm:px-7 sm:pb-14 sm:pt-[60px]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(640px_420px_at_50%_-10%,rgba(58,134,255,.14),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-50 [background-image:radial-gradient(rgba(30,94,255,.10)_1px,transparent_1px)] [background-size:30px_30px] [mask-image:radial-gradient(680px_380px_at_50%_10%,#000,transparent_72%)]"
      />

      <div className="mx-auto max-w-wrap">
        <Reveal>
          <h1 className="text-[clamp(34px,5vw,54px)] font-extrabold leading-[1.06] tracking-tight text-rs-ink">
            {coursesCatalogHero.headlineBefore}
            <span className="bg-rs-grad-cta bg-clip-text text-transparent">
              {coursesCatalogHero.headlineHighlight}
            </span>
          </h1>
          <p className="mx-auto mt-[18px] max-w-[620px] text-[18.5px] leading-relaxed text-rs-body">
            {coursesCatalogHero.sub}
          </p>
          <div className="mt-[30px] flex flex-wrap justify-center gap-3.5">
            <Button href="#courses-catalog" arrow>
              {coursesCatalogHero.primaryCta}
            </Button>
            <Button href="#bundle" variant="ghost">
              {coursesCatalogHero.secondaryCta}
            </Button>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
