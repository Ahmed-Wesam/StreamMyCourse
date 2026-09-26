import {
  BookOpen,
  CheckCircle2,
  LineChart,
  Shield,
  Users,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { aboutDifference } from '../../lib/marketing/aboutCopy'

const icons: ReactNode[] = [
  <BookOpen key="book" aria-hidden className="size-[22px]" strokeWidth={2} />,
  <LineChart key="chart" aria-hidden className="size-[22px]" strokeWidth={2} />,
  <CheckCircle2 key="check" aria-hidden className="size-[22px]" strokeWidth={2} />,
  <Users key="users" aria-hidden className="size-[22px]" strokeWidth={2} />,
  <Shield key="shield" aria-hidden className="size-[22px]" strokeWidth={2} />,
  <BookOpen key="book2" aria-hidden className="size-[22px]" strokeWidth={2} />,
]

const toneClass = {
  blue: 'border-[#e2ebff] bg-rs-grad-soft text-rs-blue',
  success: 'border-[#bce7c8] bg-[#dcf5e3] text-[#0d6f3e]',
  amber: 'border-[#f3df9a] bg-[#fff5d6] text-[#a96b00]',
} as const

export function AboutDifferenceSection() {
  return (
    <section id="difference" className="scroll-mt-24 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutDifference.kicker}
              title={aboutDifference.title}
              lead={aboutDifference.lead}
            />
          </div>
        </Reveal>

        <Reveal>
          <div className="mx-auto grid max-w-[1000px] grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {aboutDifference.cards.map((card, index) => (
              <Card
                key={card.title}
                className="rounded-rs p-6 shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:shadow-rs"
              >
                <div
                  className={[
                    'mb-4 flex size-[46px] items-center justify-center rounded-[13px] border',
                    toneClass[card.tone],
                  ].join(' ')}
                >
                  {icons[index]}
                </div>
                <h3 className="mb-2 text-base font-extrabold tracking-tight text-rs-ink">
                  {card.title}
                </h3>
                <p className="text-sm leading-relaxed text-rs-body">{card.body}</p>
              </Card>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
