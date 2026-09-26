import { Check, Info } from 'lucide-react'

import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { homeBeyond } from '../../lib/marketing/homeCopy'

export function HomeBeyondSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-[#0a1733] to-[#10245a] px-5 py-[68px] text-white sm:px-7 sm:py-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40 [background-image:radial-gradient(rgba(120,160,255,.18)_1px,transparent_1px)] [background-size:34px_34px] [mask-image:radial-gradient(800px_600px_at_50%_0,#000,transparent_75%)]"
      />
      <div className="relative mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[660px] text-center sm:mb-14">
          <Reveal>
            <span className="mb-[14px] block text-center text-[13px] font-bold uppercase tracking-[0.12em] text-[#9fc0ff]">
              {homeBeyond.kicker}
            </span>
            <h2 className="text-[clamp(28px,4vw,44px)] font-extrabold leading-[1.12] tracking-tight text-white">
              {homeBeyond.title}
            </h2>
            <p className="mx-auto mt-4 max-w-[620px] text-lg leading-relaxed text-[#b7c6e8]">
              {homeBeyond.lead}
            </p>
          </Reveal>
        </div>

        <div className="mx-auto mt-2 max-w-[760px]">
          {homeBeyond.timeline.map((item, index) => (
            <Reveal key={item.title}>
              <div className="flex flex-row items-center gap-[22px] py-3.5">
                <div
                  className={[
                    'relative z-[1] flex size-16 shrink-0 items-center justify-center rounded-[18px] border border-white/20 bg-white/5 shadow-[0_14px_30px_-12px_rgba(0,0,0,.5)] transition duration-300 ease-rs',
                    item.peak ? 'border-transparent bg-rs-grad-cta' : '',
                  ].join(' ')}
                >
                  <span
                    className={[
                      'text-sm font-extrabold tracking-wide',
                      item.peak ? 'text-white' : 'text-[#9fc0ff]',
                    ].join(' ')}
                  >
                    {item.peak ? '★' : String(index + 1).padStart(2, '0')}
                  </span>
                </div>
                <div>
                  <div className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#7fa8f5]">
                    {item.step}
                  </div>
                  <h4 className="mt-0.5 text-lg font-extrabold tracking-tight">{item.title}</h4>
                  <p className="mt-0.5 text-sm leading-snug text-[#aebbd9]">{item.body}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal className="mx-auto mt-[42px] max-w-[760px]">
          <div className="rounded-rs border border-white/15 bg-white/5 px-7 py-[26px]">
            <h5 className="mb-3.5 flex items-center gap-2 text-[15px] font-extrabold">
              <Info aria-hidden className="size-[19px] text-[#9fc0ff]" strokeWidth={2} />
              {homeBeyond.eligibilityTitle}
            </h5>
            {homeBeyond.eligibilityItems.map((item) => (
              <div
                key={item}
                className="flex items-start gap-2.5 border-b border-white/10 py-2.5 text-[14.5px] leading-snug text-[#b7c6e8] last:border-b-0"
              >
                <Check
                  aria-hidden
                  className="mt-0.5 size-4 shrink-0 text-[#7fa8f5]"
                  strokeWidth={2.2}
                />
                {item}
              </div>
            ))}
            <p className="mt-3.5 flex items-start gap-2.5 border-t border-white/15 pt-3 text-[13px] italic text-[#8597bd]">
              <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-[#7fa8f5]" strokeWidth={2.2} />
              {homeBeyond.eligibilityNote}
            </p>
          </div>
        </Reveal>

        <div className="mt-8 text-center">
          <Reveal>
            <Button
              to="/research-team"
              variant="ghost"
              className="!border-white/40 !bg-transparent !text-white hover:!bg-white/10 hover:!text-white"
            >
              {homeBeyond.learnMore}
            </Button>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
