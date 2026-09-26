import {
  BookOpen,
  Clock,
  Database,
  Grid2x2,
  LineChart,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { researchTeamProjects } from '../../lib/marketing/researchTeamCopy'

const icons: LucideIcon[] = [BookOpen, LineChart, Grid2x2, Database, Clock, BookOpen]

export function ResearchTeamProjectsSection() {
  return (
    <section id="projects" className="scroll-mt-24 px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[900px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={researchTeamProjects.kicker}
              title={researchTeamProjects.title}
              lead={researchTeamProjects.lead}
            />
          </Reveal>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {researchTeamProjects.cards.map((card, index) => {
            const Icon = icons[index]!
            return (
              <Reveal key={card.title}>
                <Card className="h-full rounded-rs px-[26px] py-7 shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:shadow-rs">
                  <div className="mb-[18px] flex size-[54px] items-center justify-center rounded-2xl border border-[#e2ebff] bg-rs-grad-soft">
                    <Icon aria-hidden className="size-[27px] text-rs-blue" strokeWidth={1.9} />
                  </div>
                  <h3 className="mb-2 text-lg font-extrabold leading-snug tracking-tight text-rs-ink">
                    {card.title}
                  </h3>
                  <p className="mb-4 text-[14.5px] leading-relaxed text-rs-body">{card.body}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {card.tags.map((tag) => (
                      <Badge key={tag} tone="blue">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </Card>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
