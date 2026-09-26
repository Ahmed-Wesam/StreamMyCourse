import { useState } from 'react'
import { Plus } from 'lucide-react'

import type { FaqItem } from '../../lib/marketing/faqCopy'

type FaqAccordionItemProps = {
  item: FaqItem
}

export function FaqAccordionItem({ item }: FaqAccordionItemProps) {
  const [open, setOpen] = useState(false)
  const panelId = `faq-panel-${item.id}`

  return (
    <div className="border-b border-rs-line first:border-t">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-5 bg-transparent py-5 text-left font-inherit"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="text-base font-bold leading-snug tracking-tight text-rs-ink">
          {item.question}
        </span>
        <span
          aria-hidden
          className={[
            'flex size-8 shrink-0 items-center justify-center rounded-full border border-rs-line text-rs-blue transition duration-200',
            open ? 'rotate-45 border-transparent bg-rs-grad-cta text-white' : 'bg-white',
          ].join(' ')}
        >
          <Plus size={16} strokeWidth={2.5} />
        </span>
      </button>
      <div id={panelId} hidden={!open} className="pb-5 pr-12">
        <p className="whitespace-pre-line text-[15.5px] leading-relaxed text-rs-body">
          {item.answer}
        </p>
      </div>
    </div>
  )
}
