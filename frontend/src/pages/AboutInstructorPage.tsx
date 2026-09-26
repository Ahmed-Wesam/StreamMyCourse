import { useCallback, useEffect, useState } from 'react'

import {
  listPublishedCourses,
  type PublicCatalogCourse,
} from '../lib/api/public-catalog'
import { usePageTitle } from '../lib/page-title'
import { AboutAudienceSection } from './about/AboutAudienceSection'
import {
  AboutCoursesSection,
  type AboutCatalogState,
} from './about/AboutCoursesSection'
import { AboutCredentialsSection } from './about/AboutCredentialsSection'
import { AboutDifferenceSection } from './about/AboutDifferenceSection'
import { AboutFinalCtaSection } from './about/AboutFinalCtaSection'
import { AboutHeroSection } from './about/AboutHeroSection'
import { AboutPresentationsSection } from './about/AboutPresentationsSection'
import { AboutPublicationsSection } from './about/AboutPublicationsSection'
import { AboutStorySection } from './about/AboutStorySection'

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load courses'
}

export default function AboutInstructorPage() {
  usePageTitle('About Instructor')

  const [catalog, setCatalog] = useState<AboutCatalogState>({ status: 'loading' })
  const [fetchKey, setFetchKey] = useState(0)

  const retry = useCallback(() => {
    setCatalog({ status: 'loading' })
    setFetchKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const courses: PublicCatalogCourse[] = await listPublishedCourses()
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
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-about">
      <AboutHeroSection />
      <AboutCredentialsSection />
      <AboutPublicationsSection />
      <AboutPresentationsSection />
      <AboutStorySection />
      <AboutCoursesSection catalog={catalog} onRetry={retry} />
      <AboutDifferenceSection />
      <AboutAudienceSection />
      <AboutFinalCtaSection />
    </div>
  )
}
