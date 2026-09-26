import type { LegalDocumentContent } from '../../lib/legal/content/types'
import { usePageTitle } from '../../lib/page-title'

type LegalDocumentPageProps = {
  content: LegalDocumentContent
}

function formatLastUpdated(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00`)
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function LegalDocumentPage({ content }: LegalDocumentPageProps) {
  usePageTitle(content.title)

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 text-rs-ink sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-rs-ink">{content.title}</h1>
        <p className="mt-2 text-sm text-rs-body">
          Last updated: {formatLastUpdated(content.lastUpdated)}
        </p>
      </div>

      <article
        data-testid="legal-prose"
        lang="en"
        className="space-y-8 text-left text-rs-body"
      >
        {content.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="text-lg font-semibold text-rs-ink">{section.heading}</h2>
            <div className="mt-3 space-y-3 text-sm leading-relaxed text-rs-body">
              {section.paragraphs.map((paragraph, index) => (
                <p key={`${section.heading}-${index}`}>{paragraph}</p>
              ))}
            </div>
          </section>
        ))}
      </article>
    </div>
  )
}
