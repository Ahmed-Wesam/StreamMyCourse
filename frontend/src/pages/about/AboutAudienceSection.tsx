import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { aboutAudience } from '../../lib/marketing/aboutCopy'

export function AboutAudienceSection() {
  return (
    <section className="border-y border-rs-line-2 bg-rs-sky-2 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutAudience.kicker}
              title={aboutAudience.title}
              lead={aboutAudience.lead}
            />
          </div>
        </Reveal>

        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {aboutAudience.cards.map((card) => (
            <Reveal key={card.title}>
              <Card className="rounded-[18px] px-5 py-[22px] shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-0.5 hover:shadow-rs">
                <h3 className="mb-1.5 text-[15.5px] font-extrabold tracking-tight text-rs-ink">
                  {card.title}
                </h3>
                <p className="text-[13.5px] leading-relaxed text-rs-body">{card.body}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
