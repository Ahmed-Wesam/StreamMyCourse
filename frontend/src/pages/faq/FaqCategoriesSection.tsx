import { Badge } from '../../components/ui/Badge'
import { Reveal } from '../../components/ui/Reveal'
import { faqCategories } from '../../lib/marketing/faqCopy'
import { FaqAccordionItem } from './FaqAccordionItem'

export function FaqCategoriesSection() {
  return (
    <div className="mx-auto max-w-wrap px-5 pb-16 sm:px-7">
      {faqCategories.map((category) => (
        <section
          key={category.id}
          id={category.anchor}
          className="scroll-mt-28 border-b border-rs-line-2 py-12 last:border-b-0 sm:py-[52px]"
        >
          <Reveal>
            <div className="mb-6 flex flex-wrap items-center gap-3">
              <h2 className="text-[22px] font-extrabold tracking-tight text-rs-ink">
                {category.title}
              </h2>
              {category.tag ? (
                <Badge tone="blue">{category.tag}</Badge>
              ) : null}
              <span className="text-xs font-semibold text-rs-muted">
                {category.items.length} questions
              </span>
            </div>
          </Reveal>
          <div>
            {category.items.map((item) => (
              <FaqAccordionItem key={item.id} item={item} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
