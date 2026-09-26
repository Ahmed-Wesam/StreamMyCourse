import {
  BarChart2,
  ClipboardList,
  GraduationCap,
  Medal,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { homeWhy } from '../../lib/marketing/homeCopy'

const icons: LucideIcon[] = [ClipboardList, BarChart2, Medal, GraduationCap, Users]

export function HomeWhySection() {
  return (
    <section className="px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[660px] sm:mb-14">
          <Reveal>
            <SectionHeader kicker={homeWhy.kicker} title={homeWhy.title} lead={homeWhy.lead} />
          </Reveal>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 nav:grid-cols-5">
          {homeWhy.features.map((feature, index) => {
            const Icon = icons[index]!
            return (
              <Reveal key={feature.title}>
                <Card className="relative h-full overflow-hidden rounded-rs px-6 py-7 shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1.5 hover:border-[#d8e3fb] hover:shadow-rs">
                  <div className="mb-4 flex size-[52px] items-center justify-center rounded-[14px] border border-[#dbe6ff] bg-rs-grad-soft">
                    <Icon aria-hidden className="size-[25px] text-rs-blue" strokeWidth={2} />
                  </div>
                  <h3 className="mb-2 text-[15.5px] font-extrabold leading-snug tracking-tight text-rs-navy">
                    {feature.title}
                  </h3>
                  <p className="text-[13.5px] leading-relaxed text-rs-body">{feature.body}</p>
                </Card>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
