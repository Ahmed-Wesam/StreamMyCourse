import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { coursesCatalogFinalCta } from '../../lib/marketing/coursesCatalogCopy'

export function CoursesCatalogFinalCtaSection() {
  return (
    <section className="px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="relative overflow-hidden rounded-rs-xl bg-rs-grad px-6 py-11 text-center shadow-rs-lg sm:px-12 sm:py-16">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 opacity-60 [background-image:radial-gradient(rgba(255,255,255,.10)_1px,transparent_1px)] [background-size:26px_26px]"
            />
            <h2 className="relative text-[clamp(28px,4vw,46px)] font-extrabold leading-tight tracking-tight text-white">
              {coursesCatalogFinalCta.title}
            </h2>
            <p className="relative mx-auto mt-4 max-w-[580px] text-lg text-[#cfe0ff]">
              {coursesCatalogFinalCta.lead}
            </p>
            <div className="relative mt-[30px] flex flex-wrap justify-center gap-3.5">
              <Button href="#courses-catalog" arrow variant="onDark">
                {coursesCatalogFinalCta.primary}
              </Button>
              <Button href="#bundle" variant="ghostOnDark">
                {coursesCatalogFinalCta.secondary}
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
