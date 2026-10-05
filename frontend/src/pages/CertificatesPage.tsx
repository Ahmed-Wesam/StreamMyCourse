import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import { getPurchases } from '../lib/api/billing'
import { getCourseProgress } from '../lib/api/catalog'
import { listMyCertificates, type MeCertificatesResponse } from '../lib/api/certificates'
import { listPublishedCourses } from '../lib/api/public-catalog'
import { getMyResearchTeam } from '../lib/api/research-team'
import { ownedCoursesFromPurchases } from '../lib/ownedFromPurchases'
import { usePageTitle } from '../lib/page-title'
import { CertificateCard } from './certificates/CertificateCard'
import { CertificateProgressCard } from './certificates/CertificateProgressCard'
import { CertificatesLockedCard, type LockedCertificateRow } from './certificates/CertificatesLockedCard'
import { CertificatesTeamBlock } from './certificates/CertificatesTeamBlock'
import type { CertificateFixture } from './certificates/certificateFixture'
import { CERT_LEARNING_HOURS, PATHWAY_COURSE_TITLES } from './certificates/courseCertificateMeta'
import { pathwayCoursesOrPrototype, type DashboardPathwayCourse } from './student-dashboard/dashboardPathway'
import './CertificatesPage.css'

const DEFAULT_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'
const DEFAULT_INSTRUCTOR_TITLE = 'Founder & Instructor, Research Spectrum'
const PATHWAY_TOTAL = PATHWAY_COURSE_TITLES.length

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready'
      data: MeCertificatesResponse
      pathwayCourses: DashboardPathwayCourse[]
      lockedRows: LockedCertificateRow[]
    }

function toFixture(item: MeCertificatesResponse['certificates'][number]): CertificateFixture {
  return {
    studentName: item.studentName,
    courseTitle: item.courseTitle,
    credentialId: item.credentialId,
    issueLabel: item.issueDate,
    instructorName: item.instructorName || DEFAULT_INSTRUCTOR_NAME,
    instructorTitle: item.instructorTitle || DEFAULT_INSTRUCTOR_TITLE,
    status: item.status,
    verifyPath: `/verify/${item.credentialId}`,
  }
}

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load certificates'
}

async function downloadCertificate(certificate: CertificateFixture): Promise<void> {
  const { generateCertificatePDF } = await import('./certificates/certificatePdf')
  generateCertificatePDF({
    name: certificate.studentName,
    title: certificate.courseTitle,
    cred: certificate.credentialId,
    date: certificate.issueLabel,
  })
}

async function copyShareLink(verifyPath: string): Promise<void> {
  const url = `${window.location.origin}${verifyPath}`
  await navigator.clipboard.writeText(url)
}

function validEarned(data: MeCertificatesResponse) {
  return data.certificates.filter((row) => row.status !== 'revoked')
}

function earnedTitles(data: MeCertificatesResponse): Set<string> {
  return new Set(validEarned(data).map((row) => row.courseTitle))
}

function learningHours(data: MeCertificatesResponse): number {
  let total = 0
  for (const row of validEarned(data)) {
    const title = row.courseTitle as (typeof PATHWAY_COURSE_TITLES)[number]
    if (title in CERT_LEARNING_HOURS) {
      total += CERT_LEARNING_HOURS[title as keyof typeof CERT_LEARNING_HOURS]
    }
  }
  return total
}

function mergePathwayCourses(
  teamCourses: DashboardPathwayCourse[],
  earned: Set<string>,
): DashboardPathwayCourse[] {
  if (teamCourses.length > 0) {
    return teamCourses.map((course) => ({
      ...course,
      certified: course.certified || earned.has(course.title),
    }))
  }
  return pathwayCoursesOrPrototype([]).map((course) => ({
    ...course,
    certified: earned.has(course.title),
  }))
}

async function loadLockedRows(
  data: MeCertificatesResponse,
  catalog: Awaited<ReturnType<typeof listPublishedCourses>>,
  purchases: Awaited<ReturnType<typeof getPurchases>>,
): Promise<{ lockedRows: LockedCertificateRow[] }> {
  const earnedIds = new Set(validEarned(data).map((row) => row.courseId))
  const earnedNames = earnedTitles(data)
  const owned = ownedCoursesFromPurchases(purchases)
  const titleToCourse = new Map<string, { id: string; title: string }>()
  for (const course of catalog) {
    titleToCourse.set(course.title, { id: course.id, title: course.title })
  }

  const quizPctByTitle = new Map<string, number>()
  for (const row of data.inProgress) {
    const pct = row.totalCount > 0 ? Math.round((row.passedCount / row.totalCount) * 100) : 0
    quizPctByTitle.set(row.courseTitle, pct)
  }

  const lockedRows: LockedCertificateRow[] = []

  for (const title of PATHWAY_COURSE_TITLES) {
    const catalogCourse = titleToCourse.get(title)
    const courseId = catalogCourse?.id ?? title
    if (earnedIds.has(courseId) || earnedNames.has(title)) continue

    const isOwned =
      owned.ownsAllPublished || (catalogCourse ? owned.courseIds.has(catalogCourse.id) : false)

    let progressPct = quizPctByTitle.get(title) ?? 0
    if (isOwned && catalogCourse) {
      try {
        const progress = await getCourseProgress(catalogCourse.id)
        progressPct = Math.max(progressPct, progress.percentComplete)
      } catch {
        /* keep quiz-only progress */
      }
    }

    lockedRows.push({
      courseId,
      title,
      owned: isOwned,
      progressPct,
      exploreHref: catalogCourse ? `/courses/${catalogCourse.id}` : '/courses#courses-catalog',
    })
  }

  return { lockedRows }
}

async function loadPageData(): Promise<Exclude<LoadState, { status: 'loading' }>> {
  const [certificatesResult, catalogResult, purchasesResult, teamResult] = await Promise.all([
    listMyCertificates(),
    listPublishedCourses().catch(() => []),
    getPurchases().catch(() => []),
    getMyResearchTeam().catch(() => ({ courses: [] })),
  ])

  const earned = earnedTitles(certificatesResult)
  const teamCourses =
    teamResult.courses.length > 0
      ? teamResult.courses.map((course) => ({
          courseId: course.courseId,
          title: course.title,
          certified: course.certified || earned.has(course.title),
          href: `/courses/${course.courseId}`,
        }))
      : []

  const pathwayCourses = mergePathwayCourses(teamCourses, earned)
  const { lockedRows } = await loadLockedRows(certificatesResult, catalogResult, purchasesResult)

  return {
    status: 'ready',
    data: certificatesResult,
    pathwayCourses,
    lockedRows,
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

function HeroMedalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </svg>
  )
}

function StatMedalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </svg>
  )
}

function StatLockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}

function StatClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

function StatPeopleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function GraduateIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z" />
      <path d="M7 5H4a2 2 0 0 0 0 4h1M17 5h3a2 2 0 0 1 0 4h-1" />
    </svg>
  )
}

function ZeroCertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="8" r="6" />
      <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export default function CertificatesPage() {
  usePageTitle('Certificates')

  const rootRef = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<LoadState>({ status: 'loading' })
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
        const next = await loadPageData()
        if (cancelled) return
        setState(next)
      } catch (err) {
        if (cancelled) return
        setState({ status: 'error', message: errorMessage(err) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fetchKey])

  const ready = state.status === 'ready' ? state : null
  const earned = ready ? validEarned(ready.data) : []
  const certCount = earned.length
  const allComplete = certCount >= PATHWAY_TOTAL
  const totalHours = ready ? learningHours(ready.data) : 0
  const profileIncompleteReady = ready
    ? ready.data.profileIncomplete.filter((item) => item.requirementsMet)
    : []

  useReveal(
    rootRef,
    `${state.status}:${certCount}:${ready?.lockedRows.length ?? 0}:${profileIncompleteReady.length}`,
  )

  return (
    <div ref={rootRef} className="pg-certificates" data-testid="student-page-certificates">
      <section className="dash-hero">
        <div className="wrap">
          <div className="dash-hi reveal">
            <HeroMedalIcon />
            Your Certificates
          </div>
          <h1 className="reveal" data-d="1">
            Your <span className="g">Certificates</span>
          </h1>
          <p className="sub reveal" data-d="2">
            Verifiable proof of your research education and achievements within Research Spectrum.
          </p>
        </div>
      </section>

      {state.status === 'loading' ? (
        <section className="db">
          <div className="wrap">
            <p className="loading-hint" role="status">
              Loading your certificates…
            </p>
          </div>
        </section>
      ) : null}

      {state.status === 'error' ? (
        <section className="db">
          <div className="wrap">
            <div className="cert-zero-banner">
              <p>{state.message}</p>
              <div className="btn-row">
                <button type="button" className="btn btn-ghost" onClick={retry}>
                  Try again
                </button>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {ready && !allComplete ? (
        <section className="db" id="cert-stat-section">
          <div className="wrap">
            <div className="stat-grid">
              <div className="stat reveal" data-d="1">
                <div className="si">
                  <StatMedalIcon />
                </div>
                <div className="lbl">Certificates Earned</div>
                <div className="val">{certCount}</div>
                <div className="vsub">of {PATHWAY_TOTAL} available</div>
              </div>
              <div className="stat reveal" data-d="2">
                <div className="si">
                  <StatLockIcon />
                </div>
                <div className="lbl">Certificates Remaining</div>
                <div className="val">{PATHWAY_TOTAL - certCount}</div>
                <div className="vsub">{certCount === PATHWAY_TOTAL ? 'all certificates earned' : 'not yet unlocked'}</div>
              </div>
              <div className="stat reveal" data-d="3">
                <div className="si">
                  <StatClockIcon />
                </div>
                <div className="lbl">Total Learning Hours</div>
                <div className="val">{totalHours || '0'}</div>
                <div className="vsub">{totalHours ? 'hours completed' : 'start a course to begin'}</div>
              </div>
              <div className="stat featured reveal" data-d="4">
                <div className="si">
                  <StatPeopleIcon />
                </div>
                <div className="lbl">Research Team Eligibility</div>
                <div className="val">{certCount === PATHWAY_TOTAL ? 'Eligible' : `${certCount}/${PATHWAY_TOTAL}`}</div>
                <div className="vsub">
                  {certCount === PATHWAY_TOTAL ? 'all 4 courses complete' : 'courses completed'}
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {ready && allComplete ? (
        <section className="db" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="cert-zero-banner grad reveal">
              <div className="czb-ic accent">
                <GraduateIcon />
              </div>
              <span className="eyebrow" style={{ marginBottom: 16 }}>
                🏆 Research Spectrum Graduate
              </span>
              <h2 style={{ marginTop: 14 }}>You&apos;ve Completed the Full Research Spectrum Pathway</h2>
              <p>
                You&apos;ve earned all four Research Spectrum certificates and are now eligible to apply to the
                Research Team.
              </p>
              <div className="btn-row">
                <Link to="/research-team" className="btn btn-primary">
                  Apply For The Research Team
                  <ArrowIcon />
                </Link>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {ready && certCount === 0 ? (
        <section className="db" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="cert-zero-banner reveal">
              <div className="czb-ic">
                <ZeroCertIcon />
              </div>
              <h2>Earn Your First Certificate</h2>
              <p>
                Complete a Research Spectrum course and successfully meet all requirements to unlock your first
                certificate.
              </p>
              <div className="btn-row">
                <Link to="/courses#courses-catalog" className="btn btn-primary">
                  Explore Courses
                  <ArrowIcon />
                </Link>
                <Link to="/dashboard" className="btn btn-ghost">
                  Back to Dashboard
                </Link>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {ready && certCount > 0 ? (
        <section className="db" id="cert-earned-section">
          <div className="wrap">
            <div className="db-head">
              <div className="ht">
                <h2>Earned Certificates</h2>
                <span className="htmeta">Your verified certificates of completion</span>
              </div>
            </div>
            <div className="cert-earned-grid">
              {earned.map((item) => {
                const certificate = toFixture(item)
                return (
                  <CertificateCard
                    key={item.id}
                    certificate={certificate}
                    onDownload={() => {
                      void downloadCertificate(certificate)
                    }}
                    onCopyShareLink={() => copyShareLink(certificate.verifyPath)}
                  />
                )
              })}
            </div>
          </div>
        </section>
      ) : null}

      {ready ? <CertificatesTeamBlock courses={ready.pathwayCourses} allComplete={allComplete} /> : null}

      {ready && !allComplete && (ready.lockedRows.length > 0 || profileIncompleteReady.length > 0) ? (
        <section className="db" id="cert-locked-section" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="db-head">
              <div className="ht">
                <h2>Complete to Unlock</h2>
                <span className="htmeta">Finish each course to earn its certificate</span>
              </div>
              <Link to="/courses#courses-catalog" className="htlink">
                Explore Courses
                <ArrowIcon />
              </Link>
            </div>
            <div className="cert-locked-grid">
              {profileIncompleteReady.map((item) => (
                <CertificateProgressCard
                  key={`profile-${item.courseId}`}
                  incomplete={{
                    courseTitle: item.courseTitle,
                    requirementsMet: true,
                    message: item.message,
                    href: item.href,
                  }}
                />
              ))}
              {ready.lockedRows.map((row, index) => (
                <CertificatesLockedCard key={row.courseId} row={row} revealDelay={index + 1} />
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  )
}
