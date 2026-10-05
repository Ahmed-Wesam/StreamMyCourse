import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import { getBundle } from '../lib/api/billing'
import { listPublishedCourses, type PublicCatalogCourse } from '../lib/api/public-catalog'
import type { BundleOffer } from '../lib/api/types'
import { formatJodMinor } from '../lib/formatJodMinor'
import { usePageTitle } from '../lib/page-title'
import './CoursesCatalogPage.css'

const BUNDLE_CHECKOUT = '/checkout?productType=bundle'

const TITLE_ORDER = [
  'research methodology',
  'statistics & spss',
  'scientific writing',
  'systematic reviews & meta-analysis',
]

const COMPARE_COLUMNS = [
  { title: 'Research Methodology', line1: 'Research', line2: 'Methodology' },
  { title: 'Statistics & SPSS', line1: 'Statistics', line2: '& SPSS' },
  { title: 'Scientific Writing', line1: 'Scientific', line2: 'Writing' },
  { title: 'Systematic Reviews & Meta-Analysis', line1: 'Systematic', line2: 'Reviews' },
] as const

type Mark = 'yes' | 'no' | 'gold'

const COMPARE_ROWS: { feature: string; marks: Mark[]; team?: boolean }[] = [
  { feature: 'Study Design', marks: ['yes', 'no', 'no', 'no', 'yes'] },
  { feature: 'Biostatistics', marks: ['no', 'yes', 'no', 'no', 'yes'] },
  { feature: 'SPSS', marks: ['no', 'yes', 'no', 'no', 'yes'] },
  { feature: 'Manuscript Writing', marks: ['no', 'no', 'yes', 'no', 'yes'] },
  { feature: 'Journal Submission', marks: ['no', 'no', 'yes', 'no', 'yes'] },
  { feature: 'Systematic Reviews', marks: ['no', 'no', 'no', 'yes', 'yes'] },
  { feature: 'Meta-Analysis', marks: ['no', 'no', 'no', 'yes', 'yes'] },
  { feature: 'Templates', marks: ['yes', 'yes', 'yes', 'yes', 'yes'] },
  { feature: 'Assignments', marks: ['yes', 'yes', 'yes', 'yes', 'yes'] },
  { feature: 'Certificate', marks: ['yes', 'yes', 'yes', 'yes', 'yes'] },
  { feature: 'Research Team Eligibility', marks: ['no', 'no', 'no', 'no', 'gold'], team: true },
]

const FEATURED_CHIPS = ['~65 Hours', 'All Levels', '4 Courses', 'Lifetime Access', 'Certificates']

const BUNDLE_INCLUDES = [
  'All Four Courses',
  'Lifetime Access',
  'Assignments',
  'Certificates',
  'Research Team Eligibility',
]

type CatalogState =
  | { status: 'loading' }
  | { status: 'ready'; courses: PublicCatalogCourse[] }
  | { status: 'error'; message: string }

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message
  return 'Failed to load courses'
}

function dollars(amountMinor: number | null | undefined): string | null {
  if (typeof amountMinor !== 'number' || !Number.isFinite(amountMinor) || amountMinor <= 0) return null
  return formatJodMinor(amountMinor)
}

function byCatalogOrder(courses: PublicCatalogCourse[]): PublicCatalogCourse[] {
  const rank = (title: string) => TITLE_ORDER.indexOf(title.trim().toLowerCase())
  return courses
    .map((course, index) => ({ course, index, rank: rank(course.title) }))
    .filter((item) => item.rank !== -1)
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((item) => item.course)
}

function priceForTitle(courses: PublicCatalogCourse[], title: string): string | null {
  const match = courses.find((course) => course.title.trim().toLowerCase() === title.toLowerCase())
  return dollars(match?.amountMinor)
}

function savingsAmount(courses: PublicCatalogCourse[], bundle: BundleOffer | null): string | null {
  if (!bundle || courses.length === 0) return null
  let sum = 0
  for (const course of courses) {
    if (typeof course.amountMinor !== 'number' || course.amountMinor <= 0) return null
    sum += course.amountMinor
  }
  const save = sum - bundle.amountMinor
  return save > 0 ? dollars(save) : null
}

function useReveal(rootRef: RefObject<HTMLElement | null>, watch: unknown) {
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
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of nodes) observer.observe(el)
    return () => observer.disconnect()
  }, [rootRef, watch])
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l2.4 7.4H22l-6 4.4 2.3 7.2L12 16.6 5.7 21l2.3-7.2-6-4.4h7.6z" />
    </svg>
  )
}

function CheckIcon({ strokeWidth }: { strokeWidth: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function MethodologyIcon({ withLines = false }: { withLines?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      {withLines ? <path d="M9 12h6M9 16h4" /> : null}
    </svg>
  )
}

function StatisticsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="13" width="3" height="5" rx="1" />
      <rect x="12" y="9" width="3" height="9" rx="1" />
      <rect x="17" y="5" width="3" height="13" rx="1" />
    </svg>
  )
}

function WritingIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

function ReviewsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

function TeamIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function iconForTitle(title: string): ReactNode {
  const key = title.trim().toLowerCase()
  if (key.includes('statistic')) return <StatisticsIcon />
  if (key.includes('writing')) return <WritingIcon />
  if (key.includes('systematic') || key.includes('meta')) return <ReviewsIcon />
  return <MethodologyIcon withLines />
}

function MarkCell({ mark }: { mark: Mark }) {
  if (mark === 'no') return <span className="no" />
  return (
    <span className={mark === 'gold' ? 'yes bundle-exclusive-check' : 'yes'}>
      <CheckIcon strokeWidth={3} />
    </span>
  )
}

function CourseCard({ course, delay }: { course: PublicCatalogCourse; delay: '1' | '2' }) {
  const level = course.level?.trim() ?? ''
  const hours =
    typeof course.estimatedHours === 'number' && course.estimatedHours > 0
      ? `~${course.estimatedHours} Hours`
      : ''
  const skills = (course.catalogSkills ?? []).map((skill) => skill.trim()).filter(Boolean)
  const price = dollars(course.amountMinor)
  const popular = course.title.trim().toLowerCase() === 'statistics & spss'
  const href = `/courses/${course.id}`

  return (
    <article className="dcard course-card reveal" data-d={delay}>
      {popular ? (
        <span className="dc-badge">
          <StarIcon /> Most Popular
        </span>
      ) : null}
      <div className="dc-top">
        <div className="cico">{iconForTitle(course.title)}</div>
        <div>
          <h3>{course.title}</h3>
          {price ? (
            <div className="dc-price">
              {price} <small>one-time</small>
            </div>
          ) : null}
        </div>
      </div>
      {course.description ? <p className="dc-desc">{course.description}</p> : null}
      {level || hours ? (
        <div className="dc-meta">
          {hours ? (
            <div className="m">
              <span className="ml">Duration</span>
              <span className="mv">{hours}</span>
            </div>
          ) : null}
          {level ? (
            <div className="m">
              <span className="ml">Level</span>
              <span className="mv">{level}</span>
            </div>
          ) : null}
        </div>
      ) : null}
      {skills.length > 0 ? (
        <div className="dc-skills">
          <div className="sk-title">Key skills learned</div>
          <ul>
            {skills.map((skill) => (
              <li key={skill}>
                <CheckIcon strokeWidth={2.4} />
                {skill}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="dc-actions">
        <Link to={href} className="btn btn-primary">
          View Course
        </Link>
        <Link to={`${href}#curriculum`} className="btn btn-ghost">
          View Curriculum
        </Link>
      </div>
    </article>
  )
}

export default function CoursesCatalogPage() {
  usePageTitle('Courses')
  const rootRef = useRef<HTMLDivElement>(null)

  const [catalog, setCatalog] = useState<CatalogState>({ status: 'loading' })
  const [fetchKey, setFetchKey] = useState(0)
  const [bundleOffer, setBundleOffer] = useState<BundleOffer | null>(null)

  const retry = useCallback(() => {
    setCatalog({ status: 'loading' })
    setFetchKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const courses = await listPublishedCourses()
        if (!cancelled) setCatalog({ status: 'ready', courses: byCatalogOrder(courses) })
      } catch (err) {
        if (!cancelled) setCatalog({ status: 'error', message: errorMessage(err) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fetchKey])

  useEffect(() => {
    let cancelled = false
    void getBundle()
      .then((offer) => {
        if (!cancelled) setBundleOffer(offer)
      })
      .catch(() => {
        if (!cancelled) setBundleOffer(null)
      })
    return () => {
      cancelled = true
    }
  }, [fetchKey])

  const courses = catalog.status === 'ready' ? catalog.courses : []
  const bundlePrice = dollars(bundleOffer?.amountMinor)
  const saveAmount = savingsAmount(courses, bundleOffer)
  useReveal(rootRef, `${catalog.status}:${courses.map((course) => course.id).join(',')}:${bundlePrice ?? ''}`)

  return (
    <div ref={rootRef} className="pg-courses" data-testid="student-page-catalog">
      <section className="phero">
        <div className="wrap">
          <h1>
            Choose Your <span className="g">Learning Path</span>
          </h1>
          <p>
            Whether you&apos;re starting your first research project or refining advanced skills, Research Spectrum
            provides a structured pathway toward independent research.
          </p>
          <div className="phero-ctas">
            <a href="#courses-catalog" className="btn btn-primary">
              Explore Courses
              <ArrowIcon />
            </a>
            <a href="#bundle" className="btn btn-ghost">
              Research Mastery Bundle
            </a>
          </div>
        </div>
      </section>

      <section className="sec" id="courses-catalog">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">All Courses</span>
            <h2 className="title reveal" data-d="1">
              Choose Your Research Path
            </h2>
            <p className="lead reveal" data-d="2">
              Take a single course to sharpen one skill, or get the complete bundle and follow the full path to
              independent research.
            </p>
          </div>

          {catalog.status === 'loading' ? <p className="lead">Loading courses…</p> : null}

          {catalog.status === 'error' ? (
            <>
              <p className="lead">{catalog.message}</p>
              <div className="phero-ctas">
                <button type="button" className="btn btn-ghost" onClick={retry}>
                  Try again
                </button>
              </div>
            </>
          ) : null}

          {catalog.status === 'ready' ? (
            <>
              {courses.length === 0 ? <p className="lead">Courses will appear here</p> : null}
              <div className="dcourse-grid">
                {courses.map((course, index) => (
                  <CourseCard key={course.id} course={course} delay={index % 2 === 0 ? '1' : '2'} />
                ))}
                <article className="dcard featured reveal" data-d="1">
                  <div className="fb-left">
                    <span className="best-tag">
                      <StarIcon /> Best Value
                    </span>
                    <h3>Research Mastery Bundle</h3>
                    <p className="fb-desc">
                      All four courses in one complete program — the full path from designing a study to publishing
                      your research, plus Research Team eligibility.
                    </p>
                    <div className="fb-chips">
                      {FEATURED_CHIPS.map((chip) => (
                        <span key={chip}>{chip}</span>
                      ))}
                    </div>
                  </div>
                  <div className="fb-right">
                    {bundlePrice ? (
                      <div className="fb-price">
                        {bundlePrice} <small>one-time payment</small>
                      </div>
                    ) : null}
                    {saveAmount ? <div className="fb-save">Save {saveAmount} vs. buying separately</div> : null}
                    <Link to={BUNDLE_CHECKOUT} className="btn btn-white">
                      Get The Bundle
                      <ArrowIcon />
                    </Link>
                  </div>
                </article>
              </div>
            </>
          ) : null}
        </div>
      </section>

      <section className="sec compare">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">Compare</span>
            <h2 className="title reveal" data-d="1">
              Compare Courses
            </h2>
            <p className="lead reveal" data-d="2">
              See exactly what each course covers — and why the bundle unlocks everything, including Research Team
              eligibility.
            </p>
          </div>
          <div className="table-scroll reveal" data-d="1">
            <table className="cmp">
              <colgroup>
                <col className="feat-col" />
                <col />
                <col />
                <col />
                <col />
                <col />
              </colgroup>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', paddingLeft: 22 }}>Feature</th>
                  {COMPARE_COLUMNS.map((column) => {
                    const price = priceForTitle(courses, column.title)
                    return (
                      <th key={column.title}>
                        {column.line1}
                        <br />
                        {column.line2}
                        {price ? <span className="pr">{price}</span> : null}
                      </th>
                    )
                  })}
                  <th className="bundle-col">
                    <span className="bundle-tag">Best Value</span>
                    <span className="bundle-name">Bundle</span>
                    {bundlePrice ? <span className="pr">{bundlePrice}</span> : null}
                    {saveAmount ? <span className="bundle-save">Save {saveAmount}</span> : null}
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARE_ROWS.map((row) => (
                  <tr key={row.feature} className={row.team ? 'rt-row' : undefined}>
                    <th>{row.feature}</th>
                    {row.marks.map((mark, index) => (
                      <td key={`${row.feature}-${index}`} className={index === 4 ? 'bundle-col' : undefined}>
                        <MarkCell mark={mark} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="sec journey">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">The Sequence</span>
            <h2 className="title reveal" data-d="1">
              Recommended Learning Path
            </h2>
            <p className="lead reveal" data-d="2">
              A structured progression designed to take you from beginner to independent researcher.
            </p>
          </div>
          <div className="road reveal" data-d="1">
            <div className="step">
              <div className="node">
                <MethodologyIcon />
              </div>
              <span className="num">STEP 01</span>
              <h4>Research Methodology</h4>
            </div>
            <div className="step">
              <div className="node">
                <StatisticsIcon />
              </div>
              <span className="num">STEP 02</span>
              <h4>Statistics & SPSS</h4>
            </div>
            <div className="step">
              <div className="node">
                <WritingIcon />
              </div>
              <span className="num">STEP 03</span>
              <h4>Scientific Writing</h4>
            </div>
            <div className="step">
              <div className="node">
                <ReviewsIcon />
              </div>
              <span className="num">STEP 04</span>
              <h4>Systematic Reviews & Meta-Analysis</h4>
            </div>
            <div className="step final">
              <div className="node">
                <TeamIcon />
              </div>
              <span className="num">GOAL</span>
              <h4>Research Team Eligibility</h4>
            </div>
          </div>
          <p className="path-note reveal" data-d="2">
            Students can take courses individually. However, <b>this sequence is the recommended progression</b> for
            learners who want to become independent researchers.
          </p>
        </div>
      </section>

      <section className="sec bundle-sec" id="bundle">
        <div className="wrap">
          <div className="bundle-card reveal">
            <div className="bc-left">
              <span className="best-tag">
                <StarIcon /> Best Value
              </span>
              <h2>Research Mastery Bundle</h2>
              <p>
                Everything you need to go from your first research question to a published paper — and become eligible
                for the Research Spectrum Research Team.
              </p>
              <ul className="bc-incl">
                {BUNDLE_INCLUDES.map((item) => (
                  <li key={item}>
                    <CheckIcon strokeWidth={2.4} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bc-right">
              <div className="lab">Complete Program</div>
              {bundlePrice ? (
                <div className="bc-price">
                  {bundlePrice} <small>one-time payment</small>
                </div>
              ) : null}
              {saveAmount ? <div className="bc-save">Save {saveAmount} vs. separately</div> : null}
              <Link to={BUNDLE_CHECKOUT} className="btn btn-white">
                Get The Bundle
                <ArrowIcon />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-band">
        <div className="wrap">
          <div className="cta-inner reveal">
            <h2>Start Building Your Research Skills Today</h2>
            <p>Choose the course that matches your current stage — or accelerate your progress with the complete bundle.</p>
            <div className="btn-w">
              <a href="#courses-catalog" className="btn btn-white">
                Explore Courses
                <ArrowIcon />
              </a>
              <Link to={BUNDLE_CHECKOUT} className="btn btn-outline-w">
                Get The Bundle
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
