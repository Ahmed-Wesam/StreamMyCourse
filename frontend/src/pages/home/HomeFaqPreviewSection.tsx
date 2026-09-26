import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { homeFaqPreview } from '../../lib/marketing/homeCopy'

export function HomeFaqPreviewSection() {
  return (
    <section className="px-5 py-[68px] sm:px-7 sm:py-24">
      <div className="mx-auto max-w-wrap">
        <div className="mx-auto mb-10 max-w-[660px] sm:mb-14">
          <Reveal>
            <SectionHeader
              kicker={homeFaqPreview.kicker}
              title={homeFaqPreview.title}
              lead={homeFaqPreview.lead}
            />
          </Reveal>
        </div>

        <Reveal>
          <div className="mx-auto mb-[30px] max-w-[760px]">
            {homeFaqPreview.items.map((item) => (
              <Card
                key={item.question}
                className="mb-3 rounded-rs px-[26px] py-[22px] shadow-rs-sm last:mb-0"
              >
                <div className="mb-2 text-[16.5px] font-extrabold tracking-tight text-rs-navy">
                  {item.question}
                </div>
                <div className="text-[14.5px] leading-relaxed text-rs-body">{item.answer}</div>
              </Card>
            ))}
          </div>
        </Reveal>

        <div className="text-center">
          <Reveal>
            <Button to="/faq" variant="ghost" arrow>
              {homeFaqPreview.viewAll}
            </Button>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
