import { useCallback, useEffect, useState } from 'react'

import { listPublishedCourses } from '../lib/api/public-catalog'
import { usePageTitle } from '../lib/page-title'
import { CoursesCatalogBundleSection } from './courses-catalog/CoursesCatalogBundleSection'
import { CoursesCatalogCompareSection } from './courses-catalog/CoursesCatalogCompareSection'
import { CoursesCatalogFinalCtaSection } from './courses-catalog/CoursesCatalogFinalCtaSection'
import {
  CoursesCatalogGridSection,
  type CatalogState,
} from './courses-catalog/CoursesCatalogGridSection'
import { CoursesCatalogHeroSection } from './courses-catalog/CoursesCatalogHeroSection'
import { CoursesCatalogJourneySection } from './courses-catalog/CoursesCatalogJourneySection'

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load courses'
}

export default function CoursesCatalogPage() {
  usePageTitle('Courses')

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

  const readyCourses = catalog.status === 'ready' ? catalog.courses : []

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-catalog">
      <CoursesCatalogHeroSection />
      <CoursesCatalogGridSection catalog={catalog} onRetry={retry} />
      <CoursesCatalogCompareSection courses={readyCourses} />
      <CoursesCatalogJourneySection />
      <CoursesCatalogBundleSection />
      <CoursesCatalogFinalCtaSection />
    </div>
  )
}
