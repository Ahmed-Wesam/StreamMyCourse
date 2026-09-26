import {
  BarChart2,
  ClipboardList,
  Eye,
  PenLine,
  Search,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { homeOutcomes } from '../../lib/marketing/homeCopy'

const icons: LucideIcon[] = [ClipboardList, BarChart2, PenLine, Search, Eye]

export function HomeOutcomesSection() {
  return (
    <section className="px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={homeOutcomes.kicker}
              title={homeOutcomes.title}
              lead={homeOutcomes.lead}
            />
          </Reveal>
        </div>
        <div className="flex flex-wrap justify-center gap-5">
          {homeOutcomes.cards.map((card, index) => {
            const Icon = icons[index]!
            return (
              <Reveal key={card.title} className="flex w-full max-w-[360px] flex-[1_1_300px]">
                <Card className="w-full rounded-rs px-[26px] py-7 shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1.5 hover:border-[#d8e3fb] hover:shadow-rs">
                  <div className="mb-[18px] flex size-[54px] items-center justify-center rounded-2xl border border-[#e2ebff] bg-rs-grad-soft">
                    <Icon aria-hidden className="size-[27px] text-rs-blue" strokeWidth={1.9} />
                  </div>
                  <h3 className="mb-2 text-lg font-extrabold leading-snug tracking-tight text-rs-ink">
                    {card.title}
                  </h3>
                  <p className="text-[14.5px] leading-relaxed text-rs-body">{card.body}</p>
                </Card>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
