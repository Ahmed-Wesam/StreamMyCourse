import { useState } from 'react'

import type { LegalDocumentContent } from '../../lib/legal/content/types'

type LegalLocale = 'en' | 'ar'

type LegalDocumentPageProps = {
  english: LegalDocumentContent
  arabic: LegalDocumentContent
}

function formatLastUpdated(isoDate: string, locale: LegalLocale): string {
  const date = new Date(`${isoDate}T00:00:00`)
  return new Intl.DateTimeFormat(locale === 'ar' ? 'ar-JO' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function LegalDocumentPage({ english, arabic }: LegalDocumentPageProps) {
  const [locale, setLocale] = useState<LegalLocale>('en')
  const content = locale === 'ar' ? arabic : english
  const lastUpdatedLabel = locale === 'ar' ? 'آخر تحديث' : 'Last updated'

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">{content.title}</h1>
          <p className="mt-2 text-sm text-gray-600">
            {lastUpdatedLabel}: {formatLastUpdated(content.lastUpdated, locale)}
          </p>
        </div>
        <div
          className="inline-flex shrink-0 rounded-lg border border-gray-200 bg-white p-1"
          role="group"
          aria-label={locale === 'ar' ? 'اختيار اللغة' : 'Language selection'}
        >
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              locale === 'en'
                ? 'bg-emerald-600 text-white'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
            aria-pressed={locale === 'en'}
            onClick={() => setLocale('en')}
          >
            English
          </button>
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              locale === 'ar'
                ? 'bg-emerald-600 text-white'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
            aria-pressed={locale === 'ar'}
            onClick={() => setLocale('ar')}
          >
            Arabic
          </button>
        </div>
      </div>

      <article
        data-testid="legal-prose"
        dir={locale === 'ar' ? 'rtl' : 'ltr'}
        lang={locale === 'ar' ? 'ar' : 'en'}
        className={`space-y-8 text-gray-800 ${locale === 'ar' ? 'text-right' : 'text-left'}`}
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
