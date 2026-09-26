import { faqCategories } from '../../lib/marketing/faqCopy'

export function FaqCategoryNav() {
  return (
    <nav
      aria-label="FAQ categories"
      className="sticky top-0 z-20 border-y border-rs-line bg-white/95 backdrop-blur-sm"
    >
      <div className="mx-auto flex max-w-wrap gap-2 overflow-x-auto px-5 py-3.5 sm:px-7">
        {faqCategories.map((category) => (
          <a
            key={category.id}
            href={`#${category.anchor}`}
            className="shrink-0 rounded-full border border-rs-line bg-white px-3.5 py-2 text-[13px] font-bold text-rs-navy transition hover:border-[#d8e3fb] hover:bg-rs-sky-2 hover:text-rs-blue"
          >
            {category.title}
          </a>
        ))}
      </div>
    </nav>
  )
}
