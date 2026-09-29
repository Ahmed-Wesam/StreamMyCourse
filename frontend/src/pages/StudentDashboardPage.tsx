import { useCallback, useEffect, useState } from 'react'

import { getCourseProgress, listCourseModules, listLessons } from '../lib/api/catalog'
import { listMyCertificates } from '../lib/api/certificates'
import { getPurchases } from '../lib/api/billing'
import { listPublishedCourses } from '../lib/api/public-catalog'
import { fetchMe } from '../lib/api/session'
import type { Course } from '../lib/api/types'
import { usePageTitle } from '../lib/page-title'
import {
  aggregateDashboardStats,
  buildDashboardCourseRows,
  ownedPublishedCoursesForDashboard,
  type CourseDashboardLoadResult,
} from '../lib/studentDashboard'
import { StudentDashboardContinueSection } from './student-dashboard/StudentDashboardContinueSection'
import { StudentDashboardHero } from './student-dashboard/StudentDashboardHero'
import { StudentDashboardStatsRow } from './student-dashboard/StudentDashboardStatsRow'
import { Button } from '../components/ui/Button'

type DashboardLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready'
      givenName: string | null
      ownedCourses: Course[]
      loadResults: CourseDashboardLoadResult[]
      /** Non-revoked count; null when the certificates request failed. */
      certificatesCount: number | null
    }

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load dashboard'
}

function publishedCatalogAsCourses(
  catalog: Awaited<ReturnType<typeof listPublishedCourses>>,
): Course[] {
  return catalog.map((course) => ({
    id: course.id,
    title: course.title,
    description: course.description,
    status: 'PUBLISHED' as const,
    thumbnailUrl: course.thumbnailUrl,
  }))
}

async function loadCourseDashboardRow(courseId: string): Promise<CourseDashboardLoadResult> {
  try {
    const [progress, lessons, modules] = await Promise.all([
      getCourseProgress(courseId),
      listLessons(courseId),
      listCourseModules(courseId),
    ])
    return {
      status: 'ok',
      courseId,
      percentComplete: progress.percentComplete,
      modules: [...modules].sort((a, b) => a.order - b.order),
      lessons: [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order),
      progress,
    }
  } catch {
    return { status: 'error', courseId }
  }
}

function countNonRevokedCertificates(
  certificates: Awaited<ReturnType<typeof listMyCertificates>>['certificates'],
): number {
  return certificates.filter((row) => row.status !== 'revoked').length
}

export default function StudentDashboardPage() {
  usePageTitle('Dashboard')

  const [state, setState] = useState<DashboardLoadState>({ status: 'loading' })
  const [fetchKey, setFetchKey] = useState(0)

  const retry = useCallback(() => {
    setState({ status: 'loading' })
    setFetchKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      setState({ status: 'loading' })
      try {
        const [catalog, purchases, meResult, certificatesResult] = await Promise.all([
          listPublishedCourses(),
          getPurchases(),
          fetchMe().then(
            (profile) => ({ ok: true as const, givenName: profile.givenName ?? null }),
            () => ({ ok: false as const, givenName: null }),
          ),
          listMyCertificates().then(
            (payload) => ({
              ok: true as const,
              count: countNonRevokedCertificates(payload.certificates),
            }),
            () => ({ ok: false as const, count: null as number | null }),
          ),
        ])
        const courses = publishedCatalogAsCourses(catalog)
        const ownedCourses = ownedPublishedCoursesForDashboard(purchases, courses)
        const loadResults = await Promise.all(ownedCourses.map((course) => loadCourseDashboardRow(course.id)))
        if (cancelled) return
        setState({
          status: 'ready',
          givenName: meResult.givenName,
          ownedCourses,
          loadResults,
          certificatesCount: certificatesResult.ok ? certificatesResult.count : null,
        })
      } catch (err) {
        if (!cancelled) {
          setState({ status: 'error', message: errorMessage(err) })
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [fetchKey])

  const ready = state.status === 'ready' ? state : null
  const stats = ready
    ? aggregateDashboardStats(ready.ownedCourses.length, ready.loadResults)
    : null
  const rows = ready ? buildDashboardCourseRows(ready.ownedCourses, ready.loadResults) : []

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-dashboard">
      <StudentDashboardHero givenName={ready?.givenName ?? null} />

      <section className="px-5 py-10 sm:px-7 sm:py-12">
        <div className="mx-auto max-w-wrap space-y-10">
          {state.status === 'loading' ? (
            <p className="text-center text-rs-body">Loading your dashboard…</p>
          ) : null}

          {state.status === 'error' ? (
            <div
              className="mx-auto flex max-w-lg flex-col items-center gap-4 text-center"
              data-testid="student-dashboard-error"
            >
              <p className="text-rs-body">{state.message}</p>
              <Button type="button" variant="ghost" onClick={retry}>
                Try again
              </Button>
            </div>
          ) : null}

          {ready ? (
            <>
              {stats ? (
                <StudentDashboardStatsRow
                  stats={stats}
                  certificatesCount={ready.certificatesCount}
                />
              ) : null}
              <div>
                <h2 className="mb-5 text-xl font-extrabold text-rs-ink">Continue learning</h2>
                <StudentDashboardContinueSection rows={rows} />
              </div>
            </>
          ) : null}
        </div>
      </section>
    </div>
  )
}
