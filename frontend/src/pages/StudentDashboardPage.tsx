import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

import { getMyActivity, type LearningActivityItem } from '../lib/api/activity'
import { getPurchases } from '../lib/api/billing'
import { getCourseProgress, listCourseModules, listLessons } from '../lib/api/catalog'
import { listMyCertificates, type MeCertificatesResponse } from '../lib/api/certificates'
import { listPublishedCourses } from '../lib/api/public-catalog'
import { getMyResearchTeam } from '../lib/api/research-team'
import { fetchMe } from '../lib/api/session'
import type { Course } from '../lib/api/types'
import { usePageTitle } from '../lib/page-title'
import {
  aggregateDashboardStats,
  buildDashboardCourseRows,
  ownedPublishedCoursesForDashboard,
  type CourseDashboardLoadResult,
} from '../lib/studentDashboard'
import { StudentDashboardActivityColumn, type DashboardCertificateCard } from './student-dashboard/StudentDashboardActivityColumn'
import { StudentDashboardContinueSection } from './student-dashboard/StudentDashboardContinueSection'
import { StudentDashboardHero } from './student-dashboard/StudentDashboardHero'
import type { DashboardPathwayCourse } from './student-dashboard/dashboardPathway'
import { StudentDashboardJourney } from './student-dashboard/StudentDashboardJourney'
import { StudentDashboardQuickRow } from './student-dashboard/StudentDashboardQuickRow'
import { StudentDashboardResearchTeamBlock } from './student-dashboard/StudentDashboardResearchTeamBlock'
import { StudentDashboardStatsRow } from './student-dashboard/StudentDashboardStatsRow'
import './StudentDashboardPage.css'

type TeamState =
  | { status: 'closed' }
  | { status: 'error' }
  | { status: 'ready'; courses: DashboardPathwayCourse[] }

type ActivityState =
  | { status: 'unavailable' }
  | { status: 'ready'; streakDays: number; items: LearningActivityItem[] }

type DashboardLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready'
      givenName: string | null
      familyName: string | null
      ownedCourses: Course[]
      loadResults: CourseDashboardLoadResult[]
      certificates: DashboardCertificateCard[] | null
      team: TeamState
      activity: ActivityState
      courseTitles: Record<string, string>
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

function visibleCertificates(
  certificates: MeCertificatesResponse['certificates'],
): DashboardCertificateCard[] {
  return certificates
    .filter((row) => row.status !== 'revoked')
    .map((row) => ({
      id: row.id,
      courseTitle: row.courseTitle,
      issueDate: row.issueDate,
    }))
}

function eligibilityLabel(team: TeamState): string {
  if (team.status !== 'ready' || team.courses.length === 0) return '—'
  const done = team.courses.filter((course) => course.certified).length
  return `${done}/${team.courses.length}`
}

async function loadDashboard(): Promise<Exclude<DashboardLoadState, { status: 'loading' }>> {
  const [catalog, purchases, meResult, certificatesResult, teamResult, activityResult] = await Promise.all([
    listPublishedCourses(),
    getPurchases(),
    fetchMe().then(
      (profile) => ({
        givenName: profile.givenName ?? null,
        familyName: profile.familyName ?? null,
      }),
      () => ({ givenName: null, familyName: null }),
    ),
    listMyCertificates().then(
      (payload) => visibleCertificates(payload.certificates),
      () => null as DashboardCertificateCard[] | null,
    ),
    getMyResearchTeam().then(
      (payload): TeamState => {
        if (payload.courses.length === 0) return { status: 'closed' }
        return {
          status: 'ready',
          courses: payload.courses.map((course) => ({
            courseId: course.courseId,
            title: course.title,
            certified: course.certified,
            href: `/courses/${course.courseId}`,
          })),
        }
      },
      (): TeamState => ({ status: 'error' }),
    ),
    getMyActivity().then(
      (activity): ActivityState => ({
        status: 'ready',
        streakDays: activity.streakDays,
        items: activity.items,
      }),
      (): ActivityState => ({ status: 'unavailable' }),
    ),
  ])
  const courses = publishedCatalogAsCourses(catalog)
  const ownedCourses = ownedPublishedCoursesForDashboard(purchases, courses)
  const loadResults = await Promise.all(ownedCourses.map((course) => loadCourseDashboardRow(course.id)))
  const courseTitles: Record<string, string> = {}
  for (const course of courses) courseTitles[course.id] = course.title
  return {
    status: 'ready',
    givenName: meResult.givenName,
    familyName: meResult.familyName,
    ownedCourses,
    loadResults,
    certificates: certificatesResult,
    team: teamResult,
    activity: activityResult,
    courseTitles,
  }
}

function useReveal(rootRef: RefObject<HTMLElement | null>, watch: string) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const nodes = Array.from(root.querySelectorAll('.reveal'))
    if (typeof IntersectionObserver === 'undefined') {
      for (const el of nodes) el.classList.add('in')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('in')
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of nodes) observer.observe(el)
    return () => observer.disconnect()
  }, [rootRef, watch])
}

function ReadySections({
  ready,
  stats,
  rows,
  streakDays,
  activityItems,
}: {
  ready: Extract<DashboardLoadState, { status: 'ready' }>
  stats: ReturnType<typeof aggregateDashboardStats>
  rows: ReturnType<typeof buildDashboardCourseRows>
  streakDays: number
  activityItems: LearningActivityItem[]
}) {
  const pathway = ready.team.status === 'ready' ? ready.team.courses : []
  return (
    <>
      <StudentDashboardStatsRow
        stats={stats}
        certificatesCount={ready.certificates ? ready.certificates.length : null}
        eligibility={eligibilityLabel(ready.team)}
      />
      <StudentDashboardContinueSection rows={rows} />
      <StudentDashboardJourney courses={pathway} />
      <StudentDashboardActivityColumn
        available={ready.activity.status === 'ready'}
        items={activityItems}
        courseTitles={ready.courseTitles}
        certificates={ready.certificates}
        pathwayCount={pathway.length}
      />
      <StudentDashboardResearchTeamBlock closed={ready.team.status === 'closed'} courses={pathway} />
      <StudentDashboardQuickRow streakDays={streakDays} />
    </>
  )
}

function DashboardView({
  state,
  onRetry,
}: {
  state: DashboardLoadState
  onRetry: () => void
}) {
  const rootRef = useRef<HTMLDivElement>(null)
  const ready = state.status === 'ready' ? state : null
  const stats = ready ? aggregateDashboardStats(ready.ownedCourses.length, ready.loadResults) : null
  const rows = ready ? buildDashboardCourseRows(ready.ownedCourses, ready.loadResults) : []
  const streakDays = ready?.activity.status === 'ready' ? ready.activity.streakDays : 0
  const activityItems = ready?.activity.status === 'ready' ? ready.activity.items : []
  useReveal(rootRef, `${state.status}:${rows.map((row) => row.courseId).join(',')}:${streakDays}:${activityItems.length}`)

  return (
    <div ref={rootRef} className="pg-dashboard" data-testid="student-page-dashboard">
      <StudentDashboardHero
        givenName={ready?.givenName ?? null}
        familyName={ready?.familyName ?? null}
        showBrowse={ready ? ready.ownedCourses.length === 0 : false}
      />

      {state.status === 'loading' ? (
        <section className="db">
          <div className="wrap">
            <p className="htmeta">Loading your dashboard…</p>
          </div>
        </section>
      ) : null}

      {state.status === 'error' ? (
        <section className="db">
          <div className="wrap">
            <div className="empty-state" data-testid="student-dashboard-error">
              <p>{state.message}</p>
              <button type="button" className="btn btn-ghost" onClick={onRetry}>
                Try again
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {ready && stats ? (
        <ReadySections
          ready={ready}
          stats={stats}
          rows={rows}
          streakDays={streakDays}
          activityItems={activityItems}
        />
      ) : null}
    </div>
  )
}

export default function StudentDashboardPage() {
  usePageTitle('Student Dashboard')

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
        const next = await loadDashboard()
        if (!cancelled) setState(next)
      } catch (err) {
        if (!cancelled) setState({ status: 'error', message: errorMessage(err) })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [fetchKey])

  return <DashboardView state={state} onRetry={retry} />
}
