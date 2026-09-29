import { Check, Star } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import type { BundleOffer } from '../../lib/api/types'
import { formatUsdMinor } from '../../lib/formatUsdMinor'
import { coursesCatalogBundle } from '../../lib/marketing/coursesCatalogCopy'

type CoursesCatalogBundleSectionProps = {
  bundleOffer: BundleOffer | null
}

export function CoursesCatalogBundleSection({ bundleOffer }: CoursesCatalogBundleSectionProps) {
  return (
    <section
      id="bundle"
      className="relative scroll-mt-24 overflow-hidden bg-gradient-to-b from-[#0a1733] to-[#10245a] px-5 py-[68px] text-white sm:px-7 sm:py-[88px]"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40 [background-image:radial-gradient(rgba(120,160,255,.18)_1px,transparent_1px)] [background-size:34px_34px] [mask-image:radial-gradient(900px_600px_at_50%_0,#000,transparent_75%)]"
      />
      <div className="relative mx-auto max-w-[980px]">
        <Reveal>
          <div className="relative grid items-center gap-10 rounded-rs-xl border border-white/15 bg-white/5 p-8 shadow-[0_50px_90px_-30px_rgba(0,0,0,.55)] sm:p-12 nav:grid-cols-[1.3fr_1fr] nav:gap-11">
            <div>
              <span className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-rs-grad-cta px-3.5 py-1.5 text-xs font-extrabold uppercase tracking-wider text-white">
                <Star aria-hidden className="size-3.5 fill-white text-white" />
                {coursesCatalogBundle.bestTag}
              </span>
              <h2 className="text-[clamp(26px,3.4vw,36px)] font-extrabold leading-tight tracking-tight">
                {coursesCatalogBundle.title}
              </h2>
              <p className="mt-3 max-w-[460px] text-[15.5px] leading-relaxed text-[#b7c6e8]">
                {coursesCatalogBundle.blurb}
              </p>
              <ul className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-x-6">
                {coursesCatalogBundle.includes.map((item) => (
                  <li key={item} className="flex items-center gap-2.5 text-sm font-semibold text-[#eaf1ff]">
                    <Check aria-hidden className="size-5 shrink-0 text-[#7fa8f5]" strokeWidth={2.4} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-rs-lg border border-white/15 bg-white/5 px-7 py-8 text-center">
              <p className="text-xs font-extrabold uppercase tracking-wider text-[#b7c6e8]">
                {coursesCatalogBundle.programLabel}
              </p>
              <p className="mt-3 text-[clamp(28px,4vw,40px)] font-extrabold leading-none tracking-tight">
                {bundleOffer ? formatUsdMinor(bundleOffer.amountMinor) : coursesCatalogBundle.accessLabel}
              </p>
              <Button to="/checkout?productType=bundle" arrow variant="onDark" className="mt-6">
                {coursesCatalogBundle.cta}
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
