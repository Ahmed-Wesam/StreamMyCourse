import {
  BarChart2,
  ClipboardList,
  PenLine,
  Search,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { homeJourney } from '../../lib/marketing/homeCopy'

const icons: LucideIcon[] = [ClipboardList, BarChart2, PenLine, Search, Users]

export function HomeJourneySection() {
  return (
    <section className="border-y border-rs-line-2 bg-rs-grad-soft px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={homeJourney.kicker}
              title={homeJourney.title}
              lead={homeJourney.lead}
            />
          </Reveal>
        </div>
        <Reveal>
          <div className="relative mt-3 grid grid-cols-1 gap-2 sm:grid-cols-5 sm:gap-0">
            <div
              aria-hidden
              className="absolute bottom-0 left-[31px] top-0 w-[3px] rounded-sm bg-gradient-to-b from-[#bcd0f7] via-rs-blue to-rs-blue-bright sm:bottom-auto sm:left-[10%] sm:right-[10%] sm:top-[31px] sm:h-[3px] sm:w-auto sm:bg-gradient-to-r"
            />
            {homeJourney.steps.map((step, index) => {
              const Icon = icons[index]!
              return (
                <div
                  key={step.title}
                  className={[
                    'relative z-[1] flex items-center gap-[18px] px-0 py-2 text-left sm:flex-col sm:gap-0 sm:px-3 sm:py-0 sm:text-center',
                  ].join(' ')}
                >
                  <div
                    className={[
                      'mx-0 flex size-16 shrink-0 items-center justify-center rounded-full border-2 bg-white shadow-rs transition duration-300 ease-rs sm:mx-auto sm:mb-[18px]',
                      step.final
                        ? 'border-transparent bg-rs-grad-cta text-white'
                        : 'border-[#d8e3fb] text-rs-blue',
                    ].join(' ')}
                  >
                    <Icon
                      aria-hidden
                      className={['size-7', step.final ? 'text-white' : 'text-rs-blue'].join(' ')}
                      strokeWidth={1.9}
                    />
                  </div>
                  <div>
                    <span className="mb-1.5 inline-block text-[11px] font-extrabold tracking-[0.1em] text-rs-blue">
                      {step.num}
                    </span>
                    <h4
                      className={[
                        'text-[15.5px] font-extrabold leading-snug tracking-tight',
                        step.final ? 'text-rs-blue' : 'text-rs-navy',
                      ].join(' ')}
                    >
                      {step.title}
                    </h4>
                  </div>
                </div>
              )
            })}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
