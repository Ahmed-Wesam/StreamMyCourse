import { useCallback, useEffect, useState } from 'react'

import {
  listPublishedCourses,
  type PublicCatalogCourse,
} from '../lib/api/public-catalog'
import { usePageTitle } from '../lib/page-title'
import { HomeBeyondSection } from './home/HomeBeyondSection'
import { HomeCoursesSection } from './home/HomeCoursesSection'
import { HomeFaqPreviewSection } from './home/HomeFaqPreviewSection'
import { HomeFinalCtaSection } from './home/HomeFinalCtaSection'
import { HomeHeroSection } from './home/HomeHeroSection'
import { HomeJourneySection } from './home/HomeJourneySection'
import { HomeOutcomesSection } from './home/HomeOutcomesSection'
import { HomeTrustBar } from './home/HomeTrustBar'
import { HomeWhySection } from './home/HomeWhySection'

type CatalogState =
  | { status: 'loading' }
  | { status: 'ready'; courses: PublicCatalogCourse[] }
  | { status: 'error'; message: string }

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load courses'
}

export default function HomePage() {
  usePageTitle()

  const [catalog, setCatalog] = useState<CatalogState>({ status: 'loading' })
  const [fetchKey, setFetchKey] = useState(0)

  const retry = useCallback(() => {
    setCatalog({ status: 'loading' })
    setFetchKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const courses = await listPublishedCourses()
        if (!cancelled) {
          setCatalog({ status: 'ready', courses })
        }
      } catch (err) {
        if (!cancelled) {
          setCatalog({ status: 'error', message: errorMessage(err) })
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [fetchKey])

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-home">
      <HomeHeroSection />
      <HomeTrustBar />
      <HomeOutcomesSection />
      <HomeJourneySection />
      <HomeCoursesSection catalog={catalog} onRetry={retry} />
      <HomeBeyondSection />
      <HomeWhySection />
      <HomeFaqPreviewSection />
      <HomeFinalCtaSection />
    </div>
  )
}
