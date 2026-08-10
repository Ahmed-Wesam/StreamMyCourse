import type { LegalDocumentContent } from '../../lib/legal/content/types'

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
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">{content.title}</h1>
        <p className="mt-2 text-sm text-gray-600">
          Last updated: {formatLastUpdated(content.lastUpdated)}
        </p>
      </div>

      <article
        data-testid="legal-prose"
        lang="en"
        className="space-y-8 text-left text-gray-800"
      >
        {content.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="text-lg font-semibold text-gray-900">{section.heading}</h2>
            <div className="mt-3 space-y-3 text-sm leading-relaxed text-gray-700">
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
