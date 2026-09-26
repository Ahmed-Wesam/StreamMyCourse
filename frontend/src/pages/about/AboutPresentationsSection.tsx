import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { aboutPresentations } from '../../lib/marketing/aboutCopy'

export function AboutPresentationsSection() {
  return (
    <section
      id="presentations"
      className="scroll-mt-24 border-y border-rs-line-2 bg-rs-sky-2 px-5 py-20 sm:px-7"
    >
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutPresentations.kicker}
              title={aboutPresentations.title}
              lead={aboutPresentations.lead}
            />
          </div>
        </Reveal>

        <Reveal>
          <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-2 lg:grid-cols-4">
            {aboutPresentations.items.map((item) => (
              <Card key={item.name} className="rounded-2xl p-6 shadow-rs-sm">
                <div className="text-[13px] font-extrabold tracking-wider text-rs-blue">
                  {item.year}
                </div>
                <div className="mt-1.5 text-[17px] font-extrabold tracking-tight text-rs-ink">
                  {item.name}
                </div>
                <div className="mt-1.5 text-sm leading-snug text-rs-muted">{item.detail}</div>
              </Card>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
