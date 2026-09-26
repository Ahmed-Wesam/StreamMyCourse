import { Button } from '../../components/ui/Button'
import { Reveal } from '../../components/ui/Reveal'
import { faqStillNeedHelp } from '../../lib/marketing/faqCopy'

export function FaqStillNeedHelpSection() {
  return (
    <section className="px-5 pb-[100px] pt-4 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="flex flex-col items-start gap-6 rounded-rs-lg border border-rs-line bg-rs-sky-2 px-6 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-9 sm:py-9">
            <div className="max-w-[560px]">
              <h2 className="text-[22px] font-extrabold tracking-tight text-rs-ink">
                {faqStillNeedHelp.title}
              </h2>
              <p className="mt-2.5 text-[15.5px] leading-relaxed text-rs-body">
                {faqStillNeedHelp.body}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-3">
              <Button to="/contact" arrow>
                {faqStillNeedHelp.primaryCta}
              </Button>
              <Button to="/courses" variant="ghost">
                {faqStillNeedHelp.secondaryCta}
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
